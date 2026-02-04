"""
FX Rate Consumer
Subscribes to Kafka topic and processes incoming FX rate messages.
"""

import os
import sys
import json
import signal
import logging
from typing import Dict, Optional

from confluent_kafka import Consumer, KafkaException, KafkaError


# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class RateProcessor:
    """
    Kafka consumer that processes FX rate messages.
    """
    
    def __init__(self):
        """Initialize Rate Processor with configuration from environment variables."""
        # Kafka configuration
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic = os.getenv('KAFKA_TOPIC', 'fx-rates')
        self.group_id = os.getenv('KAFKA_GROUP_ID', 'rate-processor-group')
        
        # Database configuration (Phase 2)
        self.database_url = os.getenv('DATABASE_URL')
        
        # Redis configuration (Phase 2)
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        
        # Initialize Kafka consumer
        self.consumer = self._create_consumer()
        
        # Shutdown flag
        self.running = True
        
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
            
            # Offset management
            'auto.offset.reset': 'earliest',  # Start from beginning if no offset stored
            'enable.auto.commit': True,        # Auto-commit offsets
            'auto.commit.interval.ms': 5000,   # Commit every 5 seconds
            
            # Consumer behavior
            'session.timeout.ms': 30000,       # 30 seconds before considered dead
            'heartbeat.interval.ms': 3000,     # Heartbeat every 3 seconds
            'max.poll.interval.ms': 300000,    # Max time between polls (5 minutes)
            
            # Message fetching
            'fetch.min.bytes': 1,              # Return as soon as data available
            'fetch.wait.max.ms': 500,          # Wait max 500ms for fetch.min.bytes
        }
        
        try:
            consumer = Consumer(config)
            logger.info("Kafka consumer created successfully")
            return consumer
        except KafkaException as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            sys.exit(1)
    
    def process_message(self, message: Dict) -> bool:
        """
        Process a single FX rate message.
        
        Args:
            message: Parsed message data
            
        Returns:
            bool: True if processing succeeded, False otherwise
        """
        try:
            timestamp = message.get('timestamp', 'N/A')
            base = message.get('base', 'N/A')
            rates = message.get('rates', {})
            source = message.get('source', 'N/A')
            
            # Print formatted output
            logger.info("=" * 60)
            logger.info(f"📊 FX Rate Update Received")
            logger.info("=" * 60)
            logger.info(f"🕐 Timestamp: {timestamp}")
            logger.info(f"💵 Base Currency: {base}")
            logger.info(f"📡 Source: {source}")
            logger.info(f"📈 Rates ({len(rates)} pairs):")
            
            # Print each currency pair
            for pair, rate in sorted(rates.items()):
                logger.info(f"   {pair:12s} = {rate:>10.4f}")
            
            logger.info("=" * 60)
            
            # Phase 2: Add database storage here
            # self._save_to_database(message)
            
            # Phase 2: Add Redis caching here
            # self._cache_latest_rates(rates)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return False
    
    def run(self):
        """
        Main consumer loop: subscribe to topic and process messages.
        """
        logger.info(f"Starting Rate Processor...")
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
                        # No message within timeout
                        continue
                    
                    if msg.error():
                        # Handle errors
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            # End of partition - not an error
                            logger.debug(f"Reached end of partition {msg.partition()} at offset {msg.offset()}")
                        else:
                            # Real error
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
        """Gracefully shutdown consumer."""
        logger.info("Shutting down consumer...")
        self.running = False
        
        try:
            # Close consumer (commits offsets and leaves group)
            self.consumer.close()
            logger.info("Consumer closed successfully")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")
        
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
