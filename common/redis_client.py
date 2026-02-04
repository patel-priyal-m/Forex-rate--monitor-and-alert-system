"""
Redis client and caching utilities.

This module provides:
- Redis connection management
- Caching helpers for FX rates, volatility, and cross-rates
- Connection testing
"""

import os
import json
from typing import Optional, Dict, List

import redis
from redis.exceptions import RedisError, ConnectionError


# Redis configuration from environment
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# Redis key prefixes for organization
KEY_PREFIX_CURRENT = "current_rate:"      # Current rate: current_rate:USD/EUR
KEY_PREFIX_VOLATILITY = "volatility:"     # Volatility: volatility:USD/EUR
KEY_PREFIX_CROSS = "cross_rate:"          # Cross rates: cross_rate:EUR/GBP
KEY_PREFIX_HISTORY = "history:"           # Historical rates list: history:USD/EUR


class RedisClient:
    """
    Redis client wrapper with caching utilities.
    """
    
    def __init__(self, host: str = REDIS_HOST, port: int = REDIS_PORT, db: int = REDIS_DB):
        """
        Initialize Redis client.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number (0-15)
        """
        self.host = host
        self.port = port
        self.db = db
        
        # Connection pool for better performance
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            decode_responses=True,  # Automatically decode bytes to strings
            max_connections=20,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        # Redis client
        self.client = redis.Redis(connection_pool=self.pool)
        
    def ping(self) -> bool:
        """
        Test Redis connection.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            return self.client.ping()
        except (RedisError, ConnectionError):
            return False
    
    def set_current_rate(self, pair: str, rate: float, ttl: int = 3600) -> bool:
        """
        Cache current FX rate.
        
        Args:
            pair: Currency pair (e.g., "USD/EUR")
            rate: Exchange rate
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            bool: True if successful
        """
        try:
            key = f"{KEY_PREFIX_CURRENT}{pair}"
            self.client.setex(key, ttl, str(rate))
            return True
        except RedisError as e:
            print(f"Error setting current rate: {e}")
            return False
    
    def get_current_rate(self, pair: str) -> Optional[float]:
        """
        Get cached current FX rate.
        
        Args:
            pair: Currency pair (e.g., "USD/EUR")
            
        Returns:
            float: Exchange rate or None if not found
        """
        try:
            key = f"{KEY_PREFIX_CURRENT}{pair}"
            value = self.client.get(key)
            return float(value) if value else None
        except (RedisError, ValueError) as e:
            print(f"Error getting current rate: {e}")
            return None
    
    def set_volatility(self, pair: str, volatility: float, ttl: int = 3600) -> bool:
        """
        Cache volatility (standard deviation) for a currency pair.
        
        Args:
            pair: Currency pair (e.g., "USD/EUR")
            volatility: Calculated volatility
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            bool: True if successful
        """
        try:
            key = f"{KEY_PREFIX_VOLATILITY}{pair}"
            self.client.setex(key, ttl, str(volatility))
            return True
        except RedisError as e:
            print(f"Error setting volatility: {e}")
            return False
    
    def get_volatility(self, pair: str) -> Optional[float]:
        """
        Get cached volatility for a currency pair.
        
        Args:
            pair: Currency pair (e.g., "USD/EUR")
            
        Returns:
            float: Volatility or None if not found
        """
        try:
            key = f"{KEY_PREFIX_VOLATILITY}{pair}"
            value = self.client.get(key)
            return float(value) if value else None
        except (RedisError, ValueError) as e:
            print(f"Error getting volatility: {e}")
            return None
    
    def set_cross_rate(self, pair: str, rate: float, ttl: int = 3600) -> bool:
        """
        Cache cross-rate (e.g., EUR/GBP calculated from USD/EUR and USD/GBP).
        
        Args:
            pair: Currency pair (e.g., "EUR/GBP")
            rate: Calculated cross rate
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            bool: True if successful
        """
        try:
            key = f"{KEY_PREFIX_CROSS}{pair}"
            self.client.setex(key, ttl, str(rate))
            return True
        except RedisError as e:
            print(f"Error setting cross rate: {e}")
            return False
    
    def get_cross_rate(self, pair: str) -> Optional[float]:
        """
        Get cached cross-rate.
        
        Args:
            pair: Currency pair (e.g., "EUR/GBP")
            
        Returns:
            float: Cross rate or None if not found
        """
        try:
            key = f"{KEY_PREFIX_CROSS}{pair}"
            value = self.client.get(key)
            return float(value) if value else None
        except (RedisError, ValueError) as e:
            print(f"Error getting cross rate: {e}")
            return None
    
    def add_to_history(self, pair: str, rate: float, max_size: int = 20) -> bool:
        """
        Add rate to historical list (for volatility calculation).
        
        Uses Redis LIST data structure (FIFO queue).
        Keeps only last N rates to calculate rolling volatility.
        
        Args:
            pair: Currency pair (e.g., "USD/EUR")
            rate: Exchange rate
            max_size: Maximum number of historical rates to keep
            
        Returns:
            bool: True if successful
        """
        try:
            key = f"{KEY_PREFIX_HISTORY}{pair}"
            
            # Add to right end of list
            self.client.rpush(key, str(rate))
            
            # Trim list to keep only last max_size elements
            self.client.ltrim(key, -max_size, -1)
            
            return True
        except RedisError as e:
            print(f"Error adding to history: {e}")
            return False
    
    def get_history(self, pair: str) -> List[float]:
        """
        Get historical rates list for volatility calculation.
        
        Args:
            pair: Currency pair (e.g., "USD/EUR")
            
        Returns:
            List[float]: List of historical rates (oldest to newest)
        """
        try:
            key = f"{KEY_PREFIX_HISTORY}{pair}"
            values = self.client.lrange(key, 0, -1)
            return [float(v) for v in values]
        except (RedisError, ValueError) as e:
            print(f"Error getting history: {e}")
            return []
    
    def get_all_current_rates(self) -> Dict[str, float]:
        """
        Get all cached current rates.
        
        Returns:
            Dict[str, float]: Dictionary of {pair: rate}
        """
        try:
            pattern = f"{KEY_PREFIX_CURRENT}*"
            keys = self.client.keys(pattern)
            
            rates = {}
            for key in keys:
                # Extract pair from key (remove prefix)
                pair = key.replace(KEY_PREFIX_CURRENT, '')
                value = self.client.get(key)
                if value:
                    rates[pair] = float(value)
            
            return rates
        except (RedisError, ValueError) as e:
            print(f"Error getting all rates: {e}")
            return {}
    
    def delete_key(self, key: str) -> bool:
        """
        Delete a specific key.
        
        Args:
            key: Redis key to delete
            
        Returns:
            bool: True if successful
        """
        try:
            self.client.delete(key)
            return True
        except RedisError as e:
            print(f"Error deleting key: {e}")
            return False
    
    def flush_all(self) -> bool:
        """
        Delete all keys in current database.
        
        WARNING: Use with caution!
        
        Returns:
            bool: True if successful
        """
        try:
            self.client.flushdb()
            return True
        except RedisError as e:
            print(f"Error flushing database: {e}")
            return False
    
    def close(self):
        """Close Redis connection pool."""
        self.pool.disconnect()


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    Get global Redis client instance (singleton pattern).
    
    Returns:
        RedisClient: Redis client instance
        
    Usage:
        redis_client = get_redis_client()
        redis_client.set_current_rate("USD/EUR", 0.92)
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = RedisClient()
    
    return _redis_client


if __name__ == '__main__':
    # Test Redis connection
    print(f"Connecting to Redis: {REDIS_HOST}:{REDIS_PORT} (db={REDIS_DB})")
    
    client = get_redis_client()
    
    if client.ping():
        print("✅ Redis connection successful")
        
        # Test operations
        print("\nTesting Redis operations...")
        
        # Set and get current rate
        client.set_current_rate("USD/EUR", 0.92)
        rate = client.get_current_rate("USD/EUR")
        print(f"Current rate USD/EUR: {rate}")
        
        # Set and get volatility
        client.set_volatility("USD/EUR", 0.015)
        vol = client.get_volatility("USD/EUR")
        print(f"Volatility USD/EUR: {vol}")
        
        # Add to history
        for r in [0.91, 0.92, 0.93, 0.92, 0.91]:
            client.add_to_history("USD/EUR", r)
        
        history = client.get_history("USD/EUR")
        print(f"History USD/EUR: {history}")
        
        print("\n✅ All Redis operations successful")
    else:
        print("❌ Redis connection failed")
