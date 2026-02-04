"""
FX Rate Producer
Fetches real-time foreign exchange rates from external API and publishes to Kafka.
"""

import os
import sys
import json
import time
import signal
import logging
from datetime import datetime
from typing import Dict, Optional

import requests
from confluent_kafka import Producer, KafkaException


# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class FXProducer:
    """
    Fetches FX rates from external API and publishes to Kafka topic.
    """
    
    def __init__(self):
        """Initialize FX Producer with configuration from environment variables."""
        # Kafka configuration
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic = os.getenv('KAFKA_TOPIC', 'fx-rates')
        
        # API configuration
        self.api_url = os.getenv('FX_API_URL', 'https://api.exchangerate-api.com/v4/latest/USD')
        self.fetch_interval = int(os.getenv('FETCH_INTERVAL', '30'))
        
        # Currency configuration
        tracked_currencies = os.getenv('TRACKED_CURRENCIES', 'EUR,GBP,JPY,CAD,AUD,CHF,CNY,INR')
        self.tracked_currencies = [c.strip() for c in tracked_currencies.split(',')]
        
        # Initialize Kafka producer
        self.producer = self._create_producer()
        
        # Shutdown flag
        self.running = True
        
        logger.info(f"FX Producer initialized")
        logger.info(f"Kafka: {self.bootstrap_servers}, Topic: {self.topic}")
        logger.info(f"API: {self.api_url}")
        logger.info(f"Tracking currencies: {', '.join(self.tracked_currencies)}")
        logger.info(f"Fetch interval: {self.fetch_interval} seconds")
    
    def _create_producer(self) -> Producer:
        """
        Create and configure Kafka producer.
        
        Returns:
            Producer: Configured Kafka producer instance
        """
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': 'fx-producer',
            
            # Delivery guarantees
            'acks': 'all',  # Wait for all replicas to acknowledge
            'retries': 3,   # Retry failed sends up to 3 times
            
            # Performance tuning
            'linger.ms': 100,        # Wait up to 100ms to batch messages
            'batch.size': 16384,     # Batch size in bytes
            'compression.type': 'snappy',  # Compress messages
            
            # Idempotence (prevents duplicate messages)
            'enable.idempotence': True,
        }
        
        try:
            producer = Producer(config)
            logger.info("Kafka producer created successfully")
            return producer
        except KafkaException as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            sys.exit(1)
    
    def delivery_callback(self, err, msg):
        """
        Callback function called when message delivery succeeds or fails.
        
        Args:
            err: Error object if delivery failed, None if successful
            msg: Message object with metadata
        """
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")
    
    def fetch_rates(self) -> Optional[Dict]:
        """
        Fetch current exchange rates from external API.
        
        Returns:
            Dict with rate data or None if fetch failed
        """
        try:
            logger.info(f"Fetching rates from {self.api_url}")
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()  # Raise exception for 4xx/5xx status codes
            
            data = response.json()
            logger.info(f"Successfully fetched rates for {len(data.get('rates', {}))} currencies")
            return data
            
        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to API")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except json.JSONDecodeError:
            logger.error("Failed to parse API response as JSON")
            return None
    
    def format_message(self, api_response: Dict) -> Dict:
        """
        Format API response into Kafka message structure.
        
        Args:
            api_response: Raw API response data
            
        Returns:
            Dict: Formatted message with timestamp, base currency, and tracked rates
        """
        all_rates = api_response.get('rates', {})
        
        # Filter only tracked currencies and format as USD/XXX pairs
        tracked_rates = {}
        for currency in self.tracked_currencies:
            if currency in all_rates:
                pair = f"USD/{currency}"
                tracked_rates[pair] = all_rates[currency]
            else:
                logger.warning(f"Currency {currency} not found in API response")
        
        message = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'base': 'USD',
            'rates': tracked_rates,
            'source': 'exchangerate-api.com'
        }
        
        return message
    
    def publish_message(self, message: Dict) -> bool:
        """
        Publish message to Kafka topic.
        
        Args:
            message: Message data to publish
            
        Returns:
            bool: True if publish initiated successfully, False otherwise
        """
        try:
            # Serialize message to JSON
            message_bytes = json.dumps(message).encode('utf-8')
            
            # Publish to Kafka (async)
            self.producer.produce(
                topic=self.topic,
                value=message_bytes,
                callback=self.delivery_callback
            )
            
            # Trigger any available delivery report callbacks
            self.producer.poll(0)
            
            logger.info(f"Published message with {len(message['rates'])} rates at {message['timestamp']}")
            return True
            
        except BufferError:
            logger.error("Producer queue is full, waiting for space...")
            self.producer.poll(1)  # Wait for queue to drain
            return False
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    def run(self):
        """
        Main producer loop: fetch rates and publish to Kafka at regular intervals.
        """
        logger.info("Starting FX Producer...")
        
        consecutive_failures = 0
        max_failures = 5
        
        while self.running:
            try:
                # Fetch rates from API
                api_response = self.fetch_rates()
                
                if api_response:
                    # Format message
                    message = self.format_message(api_response)
                    
                    # Publish to Kafka
                    if self.publish_message(message):
                        consecutive_failures = 0  # Reset failure counter
                    else:
                        consecutive_failures += 1
                else:
                    consecutive_failures += 1
                
                # Check for too many consecutive failures
                if consecutive_failures >= max_failures:
                    logger.error(f"Too many consecutive failures ({consecutive_failures}), stopping producer")
                    break
                
                # Wait before next fetch
                logger.info(f"Waiting {self.fetch_interval} seconds until next fetch...")
                time.sleep(self.fetch_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                consecutive_failures += 1
                time.sleep(self.fetch_interval)
        
        self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown producer."""
        logger.info("Shutting down producer...")
        self.running = False
        
        # Flush any pending messages
        logger.info("Flushing pending messages...")
        pending = self.producer.flush(timeout=10)
        
        if pending > 0:
            logger.warning(f"{pending} messages were not delivered")
        else:
            logger.info("All messages delivered successfully")
        
        logger.info("Producer shutdown complete")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and run producer
        producer = FXProducer()
        producer.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
