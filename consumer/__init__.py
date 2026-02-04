"""
Consumer package for processing FX rate messages from Kafka.

This package contains the Kafka consumer that:
- Subscribes to 'fx-rates' topic
- Processes incoming rate messages
- Stores data in PostgreSQL and Redis
- Triggers alerts based on rate changes
"""

__version__ = "0.1.0"
