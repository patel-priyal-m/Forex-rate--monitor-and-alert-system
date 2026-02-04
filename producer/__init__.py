"""
Producer package for fetching FX rates and publishing to Kafka.

This package contains the Kafka producer that:
- Fetches real-time exchange rates from external API
- Publishes rate data to Kafka topic 'fx-rates'
- Runs continuously with configurable intervals
"""

__version__ = "0.1.0"
