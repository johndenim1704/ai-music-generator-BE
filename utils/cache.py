"""
Redis Cache Manager
Provides caching layer for frequently accessed data
"""
import redis
import json
import logging
from typing import Optional, Any
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Create Redis client
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True
    )
    # Test connection
    redis_client.ping()
    logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Caching disabled.")
    redis_client = None


class CacheManager:
    """Redis cache manager with fallback"""
    
    def __init__(self):
        self.client = redis_client
        self.enabled = redis_client is not None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default 1 hour)
        """
        if not self.enabled:
            return False
        
        try:
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        
        Args:
            pattern: Redis pattern (e.g., "music:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern failed for {pattern}: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Clear all cache (use with caution!)"""
        if not self.enabled:
            return False
        
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False


# Global cache instance
cache = CacheManager()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        
    Usage:
        @cached(ttl=300, key_prefix="music")
        def get_music_by_id(music_id: int):
            # ... expensive operation
            return music_data
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not cache.enabled:
                return func(*args, **kwargs)
            
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(filter(None, key_parts))
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Execute function and cache result
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


# Convenience functions for common cache patterns

def cache_music_list(ttl: int = 300):
    """Cache music list for 5 minutes"""
    return cached(ttl=ttl, key_prefix="music:list")


def cache_music_detail(ttl: int = 600):
    """Cache music details for 10 minutes"""
    return cached(ttl=ttl, key_prefix="music:detail")


def cache_user_licenses(ttl: int = 300):
    """Cache user licenses for 5 minutes"""
    return cached(ttl=ttl, key_prefix="user:licenses")


def cache_genre_presets(ttl: int = 3600):
    """Cache genre presets for 1 hour (rarely changes)"""
    return cached(ttl=ttl, key_prefix="mastering:genres")


def invalidate_music_cache(music_id: Optional[int] = None):
    """Invalidate music-related caches"""
    if music_id:
        cache.delete_pattern(f"music:detail:*{music_id}*")
    cache.delete_pattern("music:list:*")
    logger.info(f"Invalidated music cache{f' for ID {music_id}' if music_id else ''}")


def invalidate_user_cache(user_id: int):
    """Invalidate user-related caches"""
    cache.delete_pattern(f"user:*:{user_id}:*")
    logger.info(f"Invalidated user cache for ID {user_id}")
