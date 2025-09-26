"""
Tests for database connection utilities
"""
import pytest
from unittest.mock import Mock, patch
from django.test import TestCase
from database.connection import (
    check_database_health,
    check_cache_health,
    get_database_stats
)


class TestDatabaseHealth(TestCase):
    """Test database health check functions"""
    
    @patch('database.connection.connection')
    def test_check_database_health_success(self, mock_conn):
        """Test successful database health check"""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        result = check_database_health()
        
        assert result is True
        mock_cursor.execute.assert_called_with("SELECT 1")
    
    @patch('database.connection.connection')
    def test_check_database_health_failure(self, mock_conn):
        """Test database health check failure"""
        mock_conn.cursor.side_effect = Exception("Database error")
        
        result = check_database_health()
        
        assert result is False


class TestCacheHealth(TestCase):
    """Test cache health check functions"""
    
    @patch('database.connection.cache')
    def test_check_cache_health_success(self, mock_cache):
        """Test successful cache health check"""
        mock_cache.set.return_value = None
        mock_cache.get.return_value = 'ok'
        
        result = check_cache_health()
        
        assert result is True
        mock_cache.set.assert_called_with('health_check', 'ok', 10)
        mock_cache.get.assert_called_with('health_check')
    
    @patch('database.connection.cache')
    def test_check_cache_health_failure(self, mock_cache):
        """Test cache health check failure"""
        mock_cache.set.side_effect = Exception("Cache error")
        
        result = check_cache_health()
        
        assert result is False
    
    @patch('database.connection.cache')
    def test_check_cache_health_wrong_value(self, mock_cache):
        """Test cache health check with wrong return value"""
        mock_cache.set.return_value = None
        mock_cache.get.return_value = 'wrong'
        
        result = check_cache_health()
        
        assert result is False


class TestDatabaseStats(TestCase):
    """Test database statistics functions"""
    
    @patch('django.db.connections')
    def test_get_database_stats_success(self, mock_connections):
        """Test successful database stats retrieval"""
        mock_conn = Mock()
        mock_conn.queries = [{'sql': 'SELECT 1', 'time': '0.001'}]
        mock_conn.vendor = 'postgresql'
        mock_conn.connection = Mock()  # Not None, so connected
        
        mock_connections.all.return_value = [('default', mock_conn)]
        
        stats = get_database_stats()
        
        assert 'default' in stats
        assert stats['default']['query_count'] == 1
        assert stats['default']['vendor'] == 'postgresql'
        assert stats['default']['is_connected'] is True
    
    @patch('django.db.connections')
    def test_get_database_stats_failure(self, mock_connections):
        """Test database stats retrieval failure"""
        mock_connections.all.side_effect = Exception("Stats error")
        
        stats = get_database_stats()
        
        assert stats == {}
    
    @patch('django.db.connections')
    def test_get_database_stats_no_queries(self, mock_connections):
        """Test database stats with no queries"""
        mock_conn = Mock()
        mock_conn.queries = []
        mock_conn.vendor = 'sqlite3'
        mock_conn.connection = None  # Not connected
        
        mock_connections.all.return_value = [('default', mock_conn)]
        
        stats = get_database_stats()
        
        assert 'default' in stats
        assert stats['default']['query_count'] == 0
        assert stats['default']['vendor'] == 'sqlite3'
        assert stats['default']['is_connected'] is False


class TestDatabaseIntegration(TestCase):
    """Test database functions with real database"""
    
    def test_real_database_health(self):
        """Test actual database health check"""
        result = check_database_health()
        
        # Should be able to connect to test database
        assert result is True
    
    def test_real_cache_health(self):
        """Test actual cache health check"""
        result = check_cache_health()
        
        # Should be able to connect to cache or fail gracefully
        assert isinstance(result, bool)
    
    def test_real_database_stats(self):
        """Test actual database stats"""
        stats = get_database_stats()
        
        # Should return a dict
        assert isinstance(stats, dict)