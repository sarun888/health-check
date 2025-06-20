"""
Integration tests for Azure ML endpoint
Tests the deployed ML health-check API endpoints
"""

import pytest
import requests
import json
import os
import time
from typing import Dict, Any

class TestMLEndpoint:
    """Integration tests for ML endpoint"""
    
    @pytest.fixture(scope="class")
    def endpoint_config(self):
        """Get endpoint configuration from environment or command line"""
        endpoint_uri = os.environ.get("ENDPOINT_URI") or pytest.config.getoption("--endpoint-uri")
        endpoint_key = os.environ.get("ENDPOINT_KEY") or pytest.config.getoption("--endpoint-key")
        
        if not endpoint_uri:
            pytest.skip("ENDPOINT_URI not provided")
        
        return {
            "uri": endpoint_uri,
            "key": endpoint_key,
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {endpoint_key}" if endpoint_key else None
            }
        }
    
    def test_health_endpoint(self, endpoint_config):
        """Test health check endpoint"""
        health_url = f"{endpoint_config['uri']}/health"
        
        response = requests.get(
            health_url,
            headers=endpoint_config["headers"],
            timeout=30
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_readiness_endpoint(self, endpoint_config):
        """Test readiness check endpoint"""
        readiness_url = f"{endpoint_config['uri']}/readiness"
        
        response = requests.get(
            readiness_url,
            headers=endpoint_config["headers"],
            timeout=30
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data
    
    def test_metrics_endpoint(self, endpoint_config):
        """Test metrics endpoint"""
        metrics_url = f"{endpoint_config['uri']}/metrics"
        
        response = requests.get(
            metrics_url,
            headers=endpoint_config["headers"],
            timeout=30
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "model_version" in data
        assert data["status"] == "active"
        assert "timestamp" in data
    
    def test_prediction_endpoint(self, endpoint_config):
        """Test prediction endpoint with valid data"""
        predict_url = f"{endpoint_config['uri']}/predict"
        
        # Valid test data
        test_data = {
            "features": [
                0.1, 0.2, 0.3, 0.4, 0.5,
                0.6, 0.7, 0.8, 0.9, 1.0,
                0.1, 0.2, 0.3, 0.4, 0.5,
                0.6, 0.7, 0.8, 0.9, 1.0
            ]
        }
        
        response = requests.post(
            predict_url,
            json=test_data,
            headers=endpoint_config["headers"],
            timeout=30
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "result" in data
        assert "prediction" in data["result"]
        assert "probabilities" in data["result"]
        assert "model_version" in data["result"]
        assert "timestamp" in data
    
    def test_prediction_endpoint_invalid_data(self, endpoint_config):
        """Test prediction endpoint with invalid data"""
        predict_url = f"{endpoint_config['uri']}/predict"
        
        # Invalid test data (wrong number of features)
        test_data = {
            "features": [0.1, 0.2, 0.3]  # Only 3 features instead of 20
        }
        
        response = requests.post(
            predict_url,
            json=test_data,
            headers=endpoint_config["headers"],
            timeout=30
        )
        
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
    
    def test_prediction_endpoint_missing_features(self, endpoint_config):
        """Test prediction endpoint with missing features"""
        predict_url = f"{endpoint_config['uri']}/predict"
        
        # Missing features
        test_data = {}
        
        response = requests.post(
            predict_url,
            json=test_data,
            headers=endpoint_config["headers"],
            timeout=30
        )
        
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
    
    def test_endpoint_performance(self, endpoint_config):
        """Test endpoint response time"""
        health_url = f"{endpoint_config['uri']}/health"
        
        start_time = time.time()
        response = requests.get(
            health_url,
            headers=endpoint_config["headers"],
            timeout=30
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 5.0  # Should respond within 5 seconds
    
    def test_concurrent_requests(self, endpoint_config):
        """Test handling of concurrent requests"""
        import concurrent.futures
        
        health_url = f"{endpoint_config['uri']}/health"
        
        def make_request():
            return requests.get(
                health_url,
                headers=endpoint_config["headers"],
                timeout=30
            )
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for response in results:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

def pytest_addoption(parser):
    """Add command line options for pytest"""
    parser.addoption(
        "--endpoint-uri",
        action="store",
        help="Azure ML endpoint URI for integration tests"
    )
    parser.addoption(
        "--endpoint-key", 
        action="store",
        help="Azure ML endpoint key for integration tests"
    ) 