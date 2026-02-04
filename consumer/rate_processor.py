"""
FX Rate Consumer (Phase 2 Enhanced)
Subscribes to Kafka topic and processes incoming FX rate messages with:
- PostgreSQL storage
- Redis caching
- Multiprocessing for cross-rate calculations
- Volatility computation
"""

import os
import sys
import json
import signal
import logging
import time
import statistics
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from multiprocessing import Pool

from confluent_kafka import Consumer, KafkaException, KafkaError

# Import from common utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.database import get_db_session, init_db, FXRate
from common.redis_client import get_redis_client


# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def calculate_cross_rate(pair_data: Tuple[str, float, str, float]) -> Tuple[str, float]:
    """
    Calculate cross-rate between two currency pairs.
    
    This function is called by multiprocessing workers in parallel.
    
    Args:
        pair_data: Tuple of (base1, rate1, base2, rate2)
                   e.g., ("USD/EUR", 0.92, "USD/GBP", 0.79)
    
    Returns:
        Tuple of (cross_pair, cross_rate)
        e.g., ("EUR/GBP", 0.8587)
    
    Formula:
        USD/EUR = 0.92 means 1 USD = 0.92 EUR
        USD/GBP = 0.79 means 1 USD = 0.79 GBP
        EUR/GBP = (USD/GBP) / (USD/EUR) = 0.79 / 0.92 = 0.8587
    """
    pair1, rate1, pair2, rate2 = pair_data
    
    # Extract currencies from pairs (USD/EUR -> EUR, USD/GBP -> GBP)
    currency1 = pair1.split('/')[1]
    currency2 = pair2.split('/')[1]
    
    # Calculate cross rate
    cross_rate = rate2 / rate1
    cross_pair = f"{currency1}/{currency2}"
    
    return (cross_pair, cross_rate)


class RateProcessor:
    """
    Enhanced Kafka consumer with database storage, caching, and parallel processing.
    """
    
    def __init__(self):
        """Initialize Rate Processor with all Phase 2 enhancements."""
        # Kafka configuration
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic = os.getenv('KAFKA_TOPIC', 'fx-rates')
        self.group_id = os.getenv('KAFKA_GROUP_ID', 'rate-processor-group')
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Initialize Redis client
        logger.info("Initializing Redis client...")
        self.redis_client = get_redis_client()
        if self.redis_client.ping():
            logger.info("✅ Redis connection successful")
        else:
            logger.error("❌ Redis connection failed")
        
        # Initialize Kafka consumer
        self.consumer = self._create_consumer()
        
        # Multiprocessing pool for parallel cross-rate calculation
        self.pool = Pool(processes=4)
        logger.info("✅ Multiprocessing pool created with 4 workers")
        
        # Shutdown flag
        self.running = True
        
        # Statistics
        self.stats = {
            'messages_processed': 0,
            'rates_stored': 0,
            'cross_rates_calculated': 0,
            'errors': 0
        }
        
        logger.info(f"Rate Processor initialized")
        logger.info(f"Kafka: {self.bootstrap_servers}, Topic: {self.topic}")
        logger.info(f"Consumer Group: {self.group_id}")
    
    def _create_consumer(self) -> Consumer:
        """
        Create and configure Kafka consumer.
        
        Returns:
            Consumer: Configured Kafka consumer instance
        """
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'client.id': 'rate-processor',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 3000,
            'max.poll.interval.ms': 300000,
            'fetch.min.bytes': 1,
            'fetch.wait.max.ms': 500,
        }
        
        try:
            consumer = Consumer(config)
            logger.info("Kafka consumer created successfully")
            return consumer
        except KafkaException as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            sys.exit(1)
    
    def store_rates_in_db(self, timestamp: str, rates: Dict[str, float]) -> int:
        """
        Store all rates in PostgreSQL database.
        
        Args:
            timestamp: ISO-8601 timestamp string
            rates: Dictionary of {pair: rate}
        
        Returns:
            int: Number of rates stored
        """
        session = get_db_session()
        stored_count = 0
        
        try:
            # Parse timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Create FXRate records
            for pair, rate in rates.items():
                fx_rate = FXRate(
                    timestamp=dt,
                    pair=pair,
                    rate=rate
                )
                session.add(fx_rate)
                stored_count += 1
            
            # Commit all at once (transaction)
            session.commit()
            logger.debug(f"Stored {stored_count} rates in database")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing rates in database: {e}")
            stored_count = 0
        finally:
            session.close()
        
        return stored_count
    
    def cache_current_rates(self, rates: Dict[str, float]) -> int:
        """
        Cache current rates in Redis.
        
        Args:
            rates: Dictionary of {pair: rate}
        
        Returns:
            int: Number of rates cached
        """
        cached_count = 0
        
        for pair, rate in rates.items():
            if self.redis_client.set_current_rate(pair, rate, ttl=3600):
                cached_count += 1
        
        logger.debug(f"Cached {cached_count} current rates in Redis")
        return cached_count
    
    def calculate_volatility(self, pair: str, current_rate: float) -> Optional[float]:
        """
        Calculate rolling volatility (standard deviation) for a currency pair.
        
        Uses last 20 rates from Redis history.
        
        Args:
            pair: Currency pair (e.g., "USD/EUR")
            current_rate: Current rate to add to history
        
        Returns:
            float: Volatility (standard deviation) or None if insufficient data
        """
        # Add current rate to history
        self.redis_client.add_to_history(pair, current_rate, max_size=20)
        
        # Get historical rates
        history = self.redis_client.get_history(pair)
        
        # Need at least 2 data points for standard deviation
        if len(history) < 2:
            return None
        
        # Calculate standard deviation
        try:
            volatility = statistics.stdev(history)
            
            # Cache volatility
            self.redis_client.set_volatility(pair, volatility, ttl=3600)
            
            return volatility
        except statistics.StatisticsError as e:
            logger.debug(f"Error calculating volatility for {pair}: {e}")
            return None
    
    def calculate_all_volatilities(self, rates: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate volatility for all currency pairs.
        
        Args:
            rates: Dictionary of {pair: rate}
        
        Returns:
            Dict[str, float]: Dictionary of {pair: volatility}
        """
        volatilities = {}
        
        for pair, rate in rates.items():
            vol = self.calculate_volatility(pair, rate)
            if vol is not None:
                volatilities[pair] = vol
        
        return volatilities
    
    def calculate_cross_rates_parallel(self, rates: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate all cross-rates using multiprocessing for parallel execution.
        
        Cross-rate: Rate between two non-USD pairs
        Example: EUR/GBP calculated from USD/EUR and USD/GBP
        
        Args:
            rates: Dictionary of {pair: rate} (all USD-based pairs)
        
        Returns:
            Dict[str, float]: Dictionary of {cross_pair: cross_rate}
        """
        start_time = time.time()
        
        # Generate all pair combinations for cross-rate calculation
        pair_combinations = []
        pairs_list = list(rates.items())
        
        for i in range(len(pairs_list)):
            for j in range(i + 1, len(pairs_list)):
                pair1, rate1 = pairs_list[i]
                pair2, rate2 = pairs_list[j]
                
                # Both pairs should have USD as base
                if pair1.startswith('USD/') and pair2.startswith('USD/'):
                    pair_combinations.append((pair1, rate1, pair2, rate2))
        
        # Calculate cross-rates in parallel using multiprocessing
        cross_rates = {}
        
        if pair_combinations:
            # Use multiprocessing pool to calculate in parallel
            results = self.pool.map(calculate_cross_rate, pair_combinations)
            
            # Convert results to dictionary
            for cross_pair, cross_rate in results:
                cross_rates[cross_pair] = cross_rate
                
                # Cache in Redis
                self.redis_client.set_cross_rate(cross_pair, cross_rate, ttl=3600)
        
        elapsed = time.time() - start_time
        logger.info(f"Calculated {len(cross_rates)} cross-rates in {elapsed:.3f}s using multiprocessing")
        
        return cross_rates
    
    def process_message(self, message: Dict) -> bool:
        """
        Process a single FX rate message with Phase 2 enhancements.
        
        Processing steps:
        1. Store rates in PostgreSQL
        2. Cache current rates in Redis
        3. Calculate volatility for each pair
        4. Calculate cross-rates using multiprocessing
        5. Print statistics
        
        Args:
            message: Parsed message data
            
        Returns:
            bool: True if processing succeeded, False otherwise
        """
        try:
            processing_start = time.time()
            
            timestamp = message.get('timestamp', 'N/A')
            base = message.get('base', 'N/A')
            rates = message.get('rates', {})
            source = message.get('source', 'N/A')
            
            # Print header
            logger.info("=" * 70)
            logger.info(f"📊 FX Rate Update Received")
            logger.info("=" * 70)
            logger.info(f"🕐 Timestamp: {timestamp}")
            logger.info(f"💵 Base Currency: {base}")
            logger.info(f"📡 Source: {source}")
            logger.info(f"📈 Processing {len(rates)} currency pairs...")
            
            # Step 1: Store in PostgreSQL
            db_start = time.time()
            stored_count = self.store_rates_in_db(timestamp, rates)
            db_time = time.time() - db_start
            logger.info(f"✅ Stored {stored_count} rates in PostgreSQL ({db_time:.3f}s)")
            
            # Step 2: Cache in Redis
            redis_start = time.time()
            cached_count = self.cache_current_rates(rates)
            redis_time = time.time() - redis_start
            logger.info(f"✅ Cached {cached_count} rates in Redis ({redis_time:.3f}s)")
            
            # Step 3: Calculate volatility
            vol_start = time.time()
            volatilities = self.calculate_all_volatilities(rates)
            vol_time = time.time() - vol_start
            logger.info(f"✅ Calculated volatility for {len(volatilities)} pairs ({vol_time:.3f}s)")
            
            # Step 4: Calculate cross-rates (parallel processing)
            cross_rates = self.calculate_cross_rates_parallel(rates)
            
            # Print some rates with volatility
            logger.info(f"\n📊 Sample Rates:")
            for i, (pair, rate) in enumerate(sorted(rates.items())[:5]):
                vol = volatilities.get(pair)
                vol_str = f"(σ={vol:.6f})" if vol is not None else "(calculating...)"
                logger.info(f"   {pair:12s} = {rate:>10.4f} {vol_str}")
            
            # Print some cross-rates
            if cross_rates:
                logger.info(f"\n🔄 Sample Cross-Rates:")
                for i, (pair, rate) in enumerate(sorted(cross_rates.items())[:5]):
                    logger.info(f"   {pair:12s} = {rate:>10.4f}")
            
            # Update statistics
            self.stats['messages_processed'] += 1
            self.stats['rates_stored'] += stored_count
            self.stats['cross_rates_calculated'] += len(cross_rates)
            
            # Total processing time
            total_time = time.time() - processing_start
            logger.info(f"\n⏱️  Total Processing Time: {total_time:.3f}s")
            logger.info(f"📊 Session Stats: {self.stats['messages_processed']} messages, "
                       f"{self.stats['rates_stored']} rates stored, "
                       f"{self.stats['cross_rates_calculated']} cross-rates calculated")
            logger.info("=" * 70)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            self.stats['errors'] += 1
            return False
    
    def run(self):
        """
        Main consumer loop: subscribe to topic and process messages.
        """
        logger.info(f"Starting Rate Processor (Phase 2 Enhanced)...")
        logger.info(f"Subscribing to topic: {self.topic}")
        
        try:
            # Subscribe to topic
            self.consumer.subscribe([self.topic])
            logger.info(f"Subscribed to topic '{self.topic}' successfully")
            
            # Main consumption loop
            while self.running:
                try:
                    # Poll for messages (timeout in seconds)
                    msg = self.consumer.poll(timeout=1.0)
                    
                    if msg is None:
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            logger.debug(f"Reached end of partition {msg.partition()} at offset {msg.offset()}")
                        else:
                            logger.error(f"Kafka error: {msg.error()}")
                        continue
                    
                    # Parse message
                    try:
                        message_data = json.loads(msg.value().decode('utf-8'))
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode message as JSON: {msg.value()}")
                        continue
                    
                    # Process message
                    logger.debug(f"Received message from partition {msg.partition()} at offset {msg.offset()}")
                    self.process_message(message_data)
                    
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, shutting down...")
                    break
                    
        except KafkaException as e:
            logger.error(f"Kafka exception: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown consumer and cleanup resources."""
        logger.info("Shutting down consumer...")
        self.running = False
        
        # Close multiprocessing pool
        logger.info("Closing multiprocessing pool...")
        self.pool.close()
        self.pool.join()
        
        # Close Kafka consumer
        try:
            self.consumer.close()
            logger.info("Consumer closed successfully")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")
        
        # Close Redis connection
        self.redis_client.close()
        
        # Print final statistics
        logger.info("=" * 70)
        logger.info("📊 Final Statistics:")
        logger.info(f"   Messages processed: {self.stats['messages_processed']}")
        logger.info(f"   Rates stored: {self.stats['rates_stored']}")
        logger.info(f"   Cross-rates calculated: {self.stats['cross_rates_calculated']}")
        logger.info(f"   Errors: {self.stats['errors']}")
        logger.info("=" * 70)
        
        logger.info("Consumer shutdown complete")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Docker stop
    
    try:
        # Create and run consumer
        processor = RateProcessor()
        processor.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
