"""
Smoke tests for production deployment
Basic tests to verify deployment is working correctly
"""

import pytest
import requests
import os
import time

class TestSmokeTests:
    """Basic smoke tests for production deployment"""
    
    @pytest.fixture(scope="class")
    def endpoint_config(self):
        """Get endpoint configuration"""
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
    
    def test_endpoint_is_alive(self, endpoint_config):
        """Test that the endpoint is responding"""
        health_url = f"{endpoint_config['uri']}/health"
        
        response = requests.get(
            health_url,
            headers=endpoint_config["headers"],
            timeout=10
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_endpoint_is_ready(self, endpoint_config):
        """Test that the endpoint is ready to serve requests"""
        readiness_url = f"{endpoint_config['uri']}/readiness"
        
        response = requests.get(
            readiness_url,
            headers=endpoint_config["headers"],
            timeout=10
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
    
    def test_basic_prediction(self, endpoint_config):
        """Test basic prediction functionality"""
        predict_url = f"{endpoint_config['uri']}/predict"
        
        # Simple test data
        test_data = {
            "features": [1.0] * 20  # 20 features with value 1.0
        }
        
        response = requests.post(
            predict_url,
            json=test_data,
            headers=endpoint_config["headers"],
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "result" in data
        assert "prediction" in data["result"]
    
    def test_response_time(self, endpoint_config):
        """Test that responses are within acceptable time limits"""
        health_url = f"{endpoint_config['uri']}/health"
        
        start_time = time.time()
        response = requests.get(
            health_url,
            headers=endpoint_config["headers"],
            timeout=10
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 3.0  # Should respond within 3 seconds

def pytest_addoption(parser):
    """Add command line options for pytest"""
    parser.addoption(
        "--endpoint-uri",
        action="store",
        help="Azure ML endpoint URI for smoke tests"
    )
    parser.addoption(
        "--endpoint-key", 
        action="store",
        help="Azure ML endpoint key for smoke tests"
    ) 