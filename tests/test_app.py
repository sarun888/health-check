#!/usr/bin/env python3
"""
Unit tests for ML Model API
"""

import pytest
import json
import numpy as np
from unittest.mock import patch, MagicMock
from app import app, MLModel

@pytest.fixture
def client():
    """Test client fixture"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def ml_model():
    """ML model fixture"""
    model = MLModel()
    return model

class TestMLModel:
    """Test cases for MLModel class"""
    
    def test_model_initialization(self, ml_model):
        """Test model initialization"""
        assert ml_model.model_version == "1.0.0"
        assert ml_model.model_path == "model.pkl"
    
    @patch('app.joblib.load')
    @patch('os.path.exists')
    def test_load_existing_model(self, mock_exists, mock_load, ml_model):
        """Test loading existing model"""
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_load.return_value = mock_model
        
        ml_model.load_model()
        
        assert ml_model.model == mock_model
        mock_load.assert_called_once_with("model.pkl")
    
    @patch('app.joblib.load')
    @patch('os.path.exists')
    @patch.object(MLModel, 'train_model')
    def test_load_model_trains_if_not_exists(self, mock_train, mock_exists, mock_load, ml_model):
        """Test model training when file doesn't exist"""
        mock_exists.return_value = False
        
        ml_model.load_model()
        
        mock_train.assert_called_once()
    
    @patch('app.joblib.dump')
    @patch('app.make_classification')
    def test_train_model(self, mock_make_classification, mock_dump, ml_model):
        """Test model training"""
        # Mock data
        X = np.random.rand(1000, 20)
        y = np.random.randint(0, 2, 1000)
        mock_make_classification.return_value = (X, y)
        
        accuracy = ml_model.train_model()
        
        assert isinstance(accuracy, float)
        assert 0.0 <= accuracy <= 1.0
        assert ml_model.model is not None
        
    def test_predict_without_model(self, ml_model):
        """Test prediction without loaded model"""
        with pytest.raises(ValueError, match="Model not loaded"):
            ml_model.predict([0.1] * 20)
    
    @patch.object(MLModel, 'load_model')
    def test_predict_with_model(self, mock_load, ml_model):
        """Test prediction with loaded model"""
        # Mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])
        ml_model.model = mock_model
        
        features = [0.1] * 20
        result = ml_model.predict(features)
        
        assert result['prediction'] == 1
        assert len(result['probabilities']) == 2
        assert result['model_version'] == "1.0.0"

class TestAPIEndpoints:
    """Test cases for API endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data
    
    def test_readiness_check_ready(self, client):
        """Test readiness check when ready"""
        response = client.get('/readiness')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ready'
        assert 'timestamp' in data
    
    @patch('app.ml_model.model', None)
    def test_readiness_check_not_ready(self, client):
        """Test readiness check when not ready"""
        response = client.get('/readiness')
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['status'] == 'not_ready'
    
    def test_predict_success(self, client):
        """Test successful prediction"""
        test_data = {
            'features': [0.1] * 20
        }
        
        response = client.post('/predict',
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'result' in data
        assert 'timestamp' in data
    
    def test_predict_missing_features(self, client):
        """Test prediction with missing features"""
        test_data = {}
        
        response = client.post('/predict',
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_predict_invalid_features_length(self, client):
        """Test prediction with invalid features length"""
        test_data = {
            'features': [0.1] * 10  # Wrong length
        }
        
        response = client.post('/predict',
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_predict_invalid_features_type(self, client):
        """Test prediction with invalid features type"""
        test_data = {
            'features': "invalid"
        }
        
        response = client.post('/predict',
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        response = client.get('/metrics')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'model_version' in data
        assert 'status' in data
        assert 'timestamp' in data
    
    @patch('app.ml_model.train_model')
    def test_retrain_success(self, mock_train, client):
        """Test successful retraining"""
        mock_train.return_value = 0.95
        
        response = client.post('/retrain')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['accuracy'] == 0.95
    
    @patch('app.ml_model.train_model')
    def test_retrain_failure(self, mock_train, client):
        """Test retraining failure"""
        mock_train.side_effect = Exception("Training failed")
        
        response = client.post('/retrain')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data

class TestIntegration:
    """Integration tests"""
    
    def test_full_workflow(self, client):
        """Test complete workflow: health -> readiness -> predict"""
        # Check health
        health_response = client.get('/health')
        assert health_response.status_code == 200
        
        # Check readiness
        ready_response = client.get('/readiness')
        assert ready_response.status_code == 200
        
        # Make prediction
        test_data = {'features': [0.1] * 20}
        predict_response = client.post('/predict',
                                     data=json.dumps(test_data),
                                     content_type='application/json')
        assert predict_response.status_code == 200
        
        # Check metrics
        metrics_response = client.get('/metrics')
        assert metrics_response.status_code == 200

if __name__ == '__main__':
    pytest.main([__file__]) 