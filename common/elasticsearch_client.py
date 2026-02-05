"""
Elasticsearch Client for FX Rate Monitoring
Handles indexing of FX rates for Kibana visualization.
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from elasticsearch import Elasticsearch, helpers


logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """
    Elasticsearch client wrapper for indexing FX rates.
    """
    
    def __init__(self):
        """Initialize Elasticsearch client."""
        self.es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        self.es_port = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
        
        # Create Elasticsearch client
        self.client = Elasticsearch(
            [f"http://{self.es_host}:{self.es_port}"],
            request_timeout=10,
            max_retries=3,
            retry_on_timeout=True
        )
        
        # Index names
        self.rates_index = "fx-rates"
        self.alerts_index = "fx-alerts"
        
        # Initialize indices
        self._init_indices()
        
        logger.info(f"Elasticsearch client initialized: {self.es_host}:{self.es_port}")
    
    def _init_indices(self):
        """Create indices with proper mappings if they don't exist."""
        # Rates index mapping
        rates_mapping = {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "pair": {"type": "keyword"},
                    "rate": {"type": "float"},
                    "volatility": {"type": "float"},
                    "source": {"type": "keyword"}
                }
            }
        }
        
        # Alerts index mapping
        alerts_mapping = {
            "mappings": {
                "properties": {
                    "triggered_at": {"type": "date"},
                    "alert_id": {"type": "integer"},
                    "pair": {"type": "keyword"},
                    "condition": {"type": "keyword"},
                    "threshold": {"type": "float"},
                    "current_rate": {"type": "float"},
                    "message": {"type": "text"}
                }
            }
        }
        
        try:
            # Create rates index
            if not self.client.indices.exists(index=self.rates_index):
                self.client.indices.create(index=self.rates_index, body=rates_mapping)
                logger.info(f"✅ Created index: {self.rates_index}")
            
            # Create alerts index
            if not self.client.indices.exists(index=self.alerts_index):
                self.client.indices.create(index=self.alerts_index, body=alerts_mapping)
                logger.info(f"✅ Created index: {self.alerts_index}")
                
        except Exception as e:
            logger.warning(f"Error initializing indices: {e}")
    
    def index_rate(self, pair: str, rate: float, timestamp: datetime, 
                   volatility: Optional[float] = None, source: str = "api") -> bool:
        """
        Index a single FX rate document.
        
        Args:
            pair: Currency pair (e.g., "USD/EUR")
            rate: Exchange rate
            timestamp: Rate timestamp
            volatility: Optional volatility value
            source: Data source
            
        Returns:
            bool: True if indexing succeeded
        """
        try:
            doc = {
                "timestamp": timestamp.isoformat(),
                "pair": pair,
                "rate": rate,
                "volatility": volatility,
                "source": source
            }
            
            self.client.index(index=self.rates_index, document=doc)
            return True
            
        except Exception as e:
            logger.error(f"Failed to index rate for {pair}: {e}")
            return False
    
    def index_rates_bulk(self, rates_data: List[Dict]) -> int:
        """
        Index multiple rates using bulk API for better performance.
        
        Args:
            rates_data: List of rate dictionaries with keys: pair, rate, timestamp, volatility
            
        Returns:
            int: Number of successfully indexed documents
        """
        try:
            actions = []
            
            for rate_info in rates_data:
                doc = {
                    "_index": self.rates_index,
                    "_source": {
                        "timestamp": rate_info['timestamp'].isoformat(),
                        "pair": rate_info['pair'],
                        "rate": rate_info['rate'],
                        "volatility": rate_info.get('volatility'),
                        "source": rate_info.get('source', 'api')
                    }
                }
                actions.append(doc)
            
            # Bulk index
            success, failed = helpers.bulk(
                self.client,
                actions,
                raise_on_error=False,
                stats_only=True
            )
            
            logger.debug(f"Bulk indexed {success} rates to Elasticsearch")
            return success
            
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return 0
    
    def index_alert(self, alert_info: Dict) -> bool:
        """
        Index a triggered alert.
        
        Args:
            alert_info: Alert information dictionary
            
        Returns:
            bool: True if indexing succeeded
        """
        try:
            doc = {
                "triggered_at": datetime.utcnow().isoformat(),
                "alert_id": alert_info.get('alert_id'),
                "pair": alert_info.get('pair'),
                "condition": alert_info.get('condition'),
                "threshold": alert_info.get('threshold'),
                "current_rate": alert_info.get('current_rate'),
                "message": alert_info.get('message')
            }
            
            self.client.index(index=self.alerts_index, document=doc)
            logger.debug(f"Indexed alert for {alert_info.get('pair')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index alert: {e}")
            return False
    
    def ping(self) -> bool:
        """
        Test Elasticsearch connection.
        
        Returns:
            bool: True if connection successful
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Elasticsearch ping failed: {e}")
            return False
    
    def close(self):
        """Close Elasticsearch client."""
        try:
            self.client.close()
            logger.info("Elasticsearch client closed")
        except Exception as e:
            logger.error(f"Error closing Elasticsearch client: {e}")


# Singleton instance
_es_client = None


def get_elasticsearch_client() -> ElasticsearchClient:
    """
    Get singleton Elasticsearch client instance.
    
    Returns:
        ElasticsearchClient: Singleton client instance
    """
    global _es_client
    
    if _es_client is None:
        _es_client = ElasticsearchClient()
    
    return _es_client


if __name__ == '__main__':
    """Test Elasticsearch client."""
    logging.basicConfig(level=logging.INFO)
    
    # Test connection
    es_client = get_elasticsearch_client()
    
    if es_client.ping():
        print("✅ Elasticsearch connection successful")
        
        # Test indexing a rate
        test_rate = es_client.index_rate(
            pair="USD/EUR",
            rate=0.8470,
            timestamp=datetime.utcnow(),
            volatility=0.001234
        )
        
        if test_rate:
            print("✅ Test rate indexed successfully")
    else:
        print("❌ Elasticsearch connection failed")
