"""
Alert Engine Consumer
Monitors FX rates from Kafka and checks if any user alerts should be triggered.

Uses multiprocessing to check multiple alerts in parallel for efficiency.
"""

import os
import sys
import json
import signal
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from multiprocessing import Pool

from confluent_kafka import Consumer, Producer, KafkaException, KafkaError

# Import from common utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.database import get_db_session, UserAlert, AlertHistory


# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def check_alert(alert_data: Tuple[int, str, str, float, float]) -> Optional[Dict]:
    """
    Check if a single alert should be triggered.
    
    This function is called by multiprocessing workers in parallel.
    
    Args:
        alert_data: Tuple of (alert_id, pair, condition, threshold, current_rate)
        
    Returns:
        Dict with alert details if triggered, None otherwise
    """
    alert_id, pair, condition, threshold, current_rate = alert_data
    
    triggered = False
    
    # Check condition
    if condition == "above" and current_rate > threshold:
        triggered = True
    elif condition == "below" and current_rate < threshold:
        triggered = True
    
    if triggered:
        return {
            "alert_id": alert_id,
            "pair": pair,
            "condition": condition,
            "threshold": threshold,
            "current_rate": current_rate,
            "message": f"{pair} went {condition} {threshold} (current: {current_rate})"
        }
    
    return None


class AlertEngine:
    """
    Alert engine that monitors rates and triggers user alerts.
    """
    
    def __init__(self):
        """Initialize Alert Engine with Kafka consumer, producer, and multiprocessing pool."""
        # Kafka configuration
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.input_topic = os.getenv('KAFKA_TOPIC', 'fx-rates')
        self.output_topic = os.getenv('ALERT_TOPIC', 'fx-alerts')
        self.group_id = os.getenv('ALERT_GROUP_ID', 'alert-engine-group')
        
        # Initialize Kafka consumer
        self.consumer = self._create_consumer()
        
        # Initialize Kafka producer for publishing triggered alerts
        self.producer = self._create_producer()
        
        # Multiprocessing pool for parallel alert checking
        self.pool = Pool(processes=2)
        logger.info("✅ Multiprocessing pool created with 2 workers")
        
        # Shutdown flag
        self.running = True
        
        # Statistics
        self.stats = {
            'messages_processed': 0,
            'alerts_checked': 0,
            'alerts_triggered': 0
        }
        
        logger.info(f"Alert Engine initialized")
        logger.info(f"Kafka: {self.bootstrap_servers}")
        logger.info(f"Input Topic: {self.input_topic}, Output Topic: {self.output_topic}")
        logger.info(f"Consumer Group: {self.group_id}")
    
    def _create_consumer(self) -> Consumer:
        """Create and configure Kafka consumer."""
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'client.id': 'alert-engine',
            'auto.offset.reset': 'latest',  # Only process new messages
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
        }
        
        try:
            consumer = Consumer(config)
            logger.info("Kafka consumer created successfully")
            return consumer
        except KafkaException as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            sys.exit(1)
    
    def _create_producer(self) -> Producer:
        """Create and configure Kafka producer for publishing alerts."""
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': 'alert-engine-producer',
        }
        
        try:
            producer = Producer(config)
            logger.info("Kafka producer created successfully")
            return producer
        except KafkaException as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            sys.exit(1)
    
    def get_active_alerts(self) -> List[UserAlert]:
        """
        Retrieve all active alerts from database.
        
        Returns:
            List[UserAlert]: List of active alert objects
        """
        session = get_db_session()
        
        try:
            alerts = session.query(UserAlert).filter(
                UserAlert.active == True
            ).all()
            
            return alerts
        finally:
            session.close()
    
    def check_alerts_parallel(self, rates: Dict[str, float]) -> List[Dict]:
        """
        Check all active alerts against current rates using multiprocessing.
        
        Args:
            rates: Dictionary of {pair: rate}
            
        Returns:
            List[Dict]: List of triggered alerts
        """
        # Get active alerts from database
        active_alerts = self.get_active_alerts()
        
        if not active_alerts:
            return []
        
        # Prepare data for parallel processing
        alert_checks = []
        for alert in active_alerts:
            if alert.pair in rates:
                current_rate = rates[alert.pair]
                alert_checks.append((
                    alert.id,
                    alert.pair,
                    alert.condition,
                    alert.threshold,
                    current_rate
                ))
        
        if not alert_checks:
            return []
        
        # Check alerts in parallel using multiprocessing
        results = self.pool.map(check_alert, alert_checks)
        
        # Filter out None results (non-triggered alerts)
        triggered_alerts = [r for r in results if r is not None]
        
        self.stats['alerts_checked'] += len(alert_checks)
        
        return triggered_alerts
    
    def log_triggered_alert(self, alert_info: Dict) -> bool:
        """
        Log triggered alert to database alert_history table.
        
        Args:
            alert_info: Alert information dictionary
            
        Returns:
            bool: True if logged successfully
        """
        session = get_db_session()
        
        try:
            history_record = AlertHistory(
                alert_id=alert_info['alert_id'],
                pair=alert_info['pair'],
                rate=alert_info['current_rate'],
                message=alert_info['message'],
                triggered_at=datetime.utcnow()
            )
            
            session.add(history_record)
            session.commit()
            
            return True
        except Exception as e:
            logger.error(f"Failed to log alert to database: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def publish_alert(self, alert_info: Dict):
        """
        Publish triggered alert to Kafka fx-alerts topic.
        
        Args:
            alert_info: Alert information dictionary
        """
        try:
            message = json.dumps(alert_info)
            self.producer.produce(
                self.output_topic,
                value=message.encode('utf-8'),
                callback=lambda err, msg: self._delivery_callback(err, msg)
            )
            self.producer.poll(0)  # Trigger delivery callbacks
        except Exception as e:
            logger.error(f"Failed to publish alert to Kafka: {e}")
    
    def _delivery_callback(self, err, msg):
        """Callback for Kafka message delivery confirmation."""
        if err:
            logger.error(f"Alert delivery failed: {err}")
        else:
            logger.debug(f"Alert published to {msg.topic()} [{msg.partition()}]")
    
    def process_message(self, message: Dict) -> bool:
        """
        Process FX rate message and check for triggered alerts.
        
        Args:
            message: Parsed rate message
            
        Returns:
            bool: True if processing succeeded
        """
        try:
            rates = message.get('rates', {})
            
            if not rates:
                return True
            
            # Check all alerts in parallel
            triggered_alerts = self.check_alerts_parallel(rates)
            
            if triggered_alerts:
                logger.info(f"🚨 {len(triggered_alerts)} ALERT(S) TRIGGERED!")
                
                for alert_info in triggered_alerts:
                    # Log to console
                    logger.warning(f"⚠️  ALERT: {alert_info['message']}")
                    
                    # Log to database
                    self.log_triggered_alert(alert_info)
                    
                    # Publish to Kafka
                    self.publish_alert(alert_info)
                    
                    self.stats['alerts_triggered'] += 1
            
            self.stats['messages_processed'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return False
    
    def run(self):
        """Main alert engine loop."""
        logger.info(f"Starting Alert Engine...")
        logger.info(f"Subscribing to topic: {self.input_topic}")
        
        try:
            # Subscribe to topic
            self.consumer.subscribe([self.input_topic])
            logger.info(f"Subscribed to topic '{self.input_topic}' successfully")
            
            # Main consumption loop
            while self.running:
                try:
                    # Poll for messages
                    msg = self.consumer.poll(timeout=1.0)
                    
                    if msg is None:
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            continue
                        else:
                            logger.error(f"Kafka error: {msg.error()}")
                        continue
                    
                    # Parse message
                    try:
                        message_data = json.loads(msg.value().decode('utf-8'))
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode message as JSON")
                        continue
                    
                    # Process message
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
        """Gracefully shutdown alert engine."""
        logger.info("Shutting down alert engine...")
        self.running = False
        
        # Flush producer
        logger.info("Flushing producer...")
        self.producer.flush(timeout=10)
        
        # Close multiprocessing pool
        logger.info("Closing multiprocessing pool...")
        self.pool.close()
        self.pool.join()
        
        # Close consumer
        try:
            self.consumer.close()
            logger.info("Consumer closed successfully")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")
        
        # Print final statistics
        logger.info("=" * 70)
        logger.info("📊 Final Statistics:")
        logger.info(f"   Messages processed: {self.stats['messages_processed']}")
        logger.info(f"   Alerts checked: {self.stats['alerts_checked']}")
        logger.info(f"   Alerts triggered: {self.stats['alerts_triggered']}")
        logger.info("=" * 70)
        
        logger.info("Alert engine shutdown complete")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and run alert engine
        engine = AlertEngine()
        engine.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
