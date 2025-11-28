"""
Tests for caching utilities (Redis and in-memory fallback).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.utils.cache import get_cache, InMemoryCache, RedisCache


class TestInMemoryCache:
    """Tests for in-memory cache implementation"""

    def test_get_set_delete(self):
        """Test basic cache operations"""
        cache = InMemoryCache()
        
        # Test set and get
        cache.set("test_key", "test_value", ttl=3600)
        assert cache.get("test_key") == "test_value"
        
        # Test delete
        cache.delete("test_key")
        assert cache.get("test_key") is None
        
    def test_expiration(self):
        """Test that expired entries are not returned"""
        cache = InMemoryCache(default_ttl=1)
        
        cache.set("expired_key", "value", ttl=0.1)  # Very short TTL
        assert cache.get("expired_key") == "value"
        
        import time
        time.sleep(0.2)
        assert cache.get("expired_key") is None
        
    def test_exists(self):
        """Test exists method"""
        cache = InMemoryCache()
        
        assert cache.exists("nonexistent") is False
        cache.set("existing", "value")
        assert cache.exists("existing") is True
        
    def test_clear(self):
        """Test clearing all cache"""
        cache = InMemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestRedisCache:
    """Tests for Redis cache implementation"""

    @patch('app.utils.cache.redis')
    def test_redis_connection_success(self, mock_redis):
        """Test successful Redis connection"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.Redis.return_value = mock_client
        
        cache = RedisCache("redis://localhost:6379/0")
        
        assert cache._connected is True
        mock_client.ping.assert_called_once()
        
    @patch('app.utils.cache.redis')
    def test_redis_connection_failure(self, mock_redis):
        """Test Redis connection failure falls back to in-memory"""
        mock_redis.Redis.side_effect = Exception("Connection failed")
        
        cache = RedisCache("redis://localhost:6379/0")
        
        assert cache._connected is False
        assert hasattr(cache, '_fallback')
        
    @patch('app.utils.cache.redis')
    def test_redis_get_set(self, mock_redis):
        """Test Redis get and set operations"""
        import pickle
        
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.Redis.return_value = mock_client
        
        cache = RedisCache("redis://localhost:6379/0")
        
        # Test set
        cache.set("test_key", "test_value", ttl=3600)
        mock_client.setex.assert_called_once()
        args, kwargs = mock_client.setex.call_args
        assert args[0] == "test_key"
        assert args[1] == 3600
        assert pickle.loads(args[2]) == "test_value"
        
        # Test get
        mock_client.get.return_value = pickle.dumps("test_value")
        result = cache.get("test_key")
        assert result == "test_value"
        mock_client.get.assert_called_with("test_key")
        
    @patch('app.utils.cache.redis')
    def test_redis_fallback_on_error(self, mock_redis):
        """Test that Redis errors fall back to in-memory cache"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.side_effect = Exception("Redis error")
        mock_redis.Redis.return_value = mock_client
        
        cache = RedisCache("redis://localhost:6379/0")
        
        # Should not raise, but return None
        result = cache.get("test_key")
        assert result is None


class TestCacheIntegration:
    """Integration tests for cache utilities"""

    @patch('app.utils.cache.current_app')
    def test_get_cache_with_redis_enabled(self, mock_app):
        """Test get_cache when Redis is enabled"""
        mock_config = {
            'REDIS_ENABLED': True,
            'REDIS_URL': 'redis://localhost:6379/0',
            'REDIS_DEFAULT_TTL': 3600
        }
        mock_app.config = mock_config
        
        with patch('app.utils.cache.RedisCache') as mock_redis_cache:
            mock_instance = MagicMock()
            mock_instance._connected = True
            mock_redis_cache.return_value = mock_instance
            
            cache = get_cache()
            assert cache is not None
            
    @patch('app.utils.cache.current_app')
    def test_get_cache_fallback_to_memory(self, mock_app):
        """Test get_cache falls back to in-memory when Redis unavailable"""
        mock_config = {
            'REDIS_ENABLED': False,
            'REDIS_DEFAULT_TTL': 3600
        }
        mock_app.config = mock_config
        
        # Reset global cache
        import app.utils.cache
        app.utils.cache._cache = None
        
        cache = get_cache()
        assert isinstance(cache, InMemoryCache)
        
    def test_cache_decorator(self):
        """Test the @cached decorator"""
        from app.utils.cache import cached
        
        call_count = [0]
        
        @cached(ttl=60, key_prefix="test")
        def expensive_function(x, y):
            call_count[0] += 1
            return x + y
        
        # First call should execute function
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count[0] == 1
        
        # Second call should use cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count[0] == 1  # Should not increment
        
        # Different args should execute again
        result3 = expensive_function(2, 3)
        assert result3 == 5
        assert call_count[0] == 2

