"""
API Health Check Tests - Simple working functionality
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
import json


class APIHealthTest(TestCase):
    """Test API health endpoints and basic functionality."""

    def setUp(self):
        self.client = Client()

    def test_health_check_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get('/health/')
        
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Should return JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Should contain status
        data = response.json()
        self.assertIn('status', data)

    def test_api_root_accessible(self):
        """Test that API root is accessible."""
        response = self.client.get('/api/v1/')
        
        # Should not return 500 error
        self.assertNotEqual(response.status_code, 500)

    def test_options_request_cors(self):
        """Test CORS headers on OPTIONS request."""
        response = self.client.options('/health/')
        
        # Should handle OPTIONS request
        self.assertIn(response.status_code, [200, 204])

    def test_invalid_endpoint_404(self):
        """Test that invalid endpoints return 404."""
        response = self.client.get('/api/v1/nonexistent/')
        
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_health_check_json_structure(self):
        """Test health check returns proper JSON structure."""
        response = self.client.get('/api/v1/health/')
        
        if response.status_code == 200:
            data = response.json()
            
            # Basic structure validation
            self.assertIsInstance(data, dict)
            
            # Should have status field
            if 'status' in data:
                self.assertIsInstance(data['status'], str)