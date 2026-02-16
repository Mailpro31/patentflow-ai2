import redis.asyncio as redis
from typing import Optional, List, Any
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Centralized Redis cache service for storing and retrieving data.
    Handles JSON serialization, TTL management, and error handling.
    """
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._redis.ping()
                logger.info("Redis cache connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        
        return self._redis
    
    async def get(self, key: str) -> Optional[dict]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value as dict, or None if not found
        """
        try:
            client = await self._get_redis()
            value = await client.get(key)
            
            if value:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache miss for key: {key}")
                return None
                
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default from settings)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_redis()
            ttl = ttl or settings.REDIS_CACHE_TTL
            
            serialized = json.dumps(value)
            await client.setex(key, ttl, serialized)
            
            logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            client = await self._get_redis()
            result = await client.delete(key)
            
            if result:
                logger.debug(f"Cache deleted for key: {key}")
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            client = await self._get_redis()
            result = await client.exists(key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def get_many(self, keys: List[str]) -> List[Optional[dict]]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            List of values (None for missing keys)
        """
        try:
            client = await self._get_redis()
            values = await client.mget(keys)
            
            results = []
            for i, value in enumerate(values):
                if value:
                    try:
                        results.append(json.loads(value))
                        logger.debug(f"Cache hit for key: {keys[i]}")
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode cached value for key: {keys[i]}")
                        results.append(None)
                else:
                    logger.debug(f"Cache miss for key: {keys[i]}")
                    results.append(None)
            
            return results
            
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return [None] * len(keys)
    
    async def set_many(self, items: dict, ttl: Optional[int] = None) -> bool:
        """
        Set multiple values in cache.
        
        Args:
            items: Dictionary of key-value pairs
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_redis()
            ttl = ttl or settings.REDIS_CACHE_TTL
            
            # Use pipeline for efficiency
            async with client.pipeline() as pipe:
                for key, value in items.items():
                    serialized = json.dumps(value)
                    pipe.setex(key, ttl, serialized)
                
                await pipe.execute()
            
            logger.debug(f"Cache set_many for {len(items)} keys (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "patent:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            client = await self._get_redis()
            keys = []
            
            # Scan for matching keys
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await client.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching pattern: {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear_pattern error for pattern {pattern}: {e}")
            return 0
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis cache connection closed")


# Global instance
cache_service = CacheService()
