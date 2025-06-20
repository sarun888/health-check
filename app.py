import os
import logging
import joblib
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class MLModel:
    def __init__(self):
        self.model = None
        self.model_version = "1.0.0"
        self.model_path = "model.pkl"
        
    def train_model(self):
        """Train a sample model for demonstration"""
        logger.info("Training model...")
        
        # Generate sample data
        X, y = make_classification(n_samples=1000, n_features=20, n_informative=10, 
                                 n_redundant=10, n_clusters_per_class=1, random_state=42)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train model
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Model trained with accuracy: {accuracy:.4f}")
        
        # Save model
        joblib.dump(self.model, self.model_path)
        logger.info(f"Model saved to {self.model_path}")
        
        return accuracy
    
    def load_model(self):
        """Load existing model or train new one"""
        if os.path.exists(self.model_path):
            logger.info("Loading existing model...")
            self.model = joblib.load(self.model_path)
        else:
            logger.info("No existing model found, training new model...")
            self.train_model()
    
    def predict(self, features):
        """Make prediction"""
        if self.model is None:
            raise ValueError("Model not loaded")
        
        prediction = self.model.predict([features])
        probabilities = self.model.predict_proba([features])
        
        return {
            'prediction': int(prediction[0]),
            'probabilities': probabilities[0].tolist(),
            'model_version': self.model_version
        }

# Initialize ML model
ml_model = MLModel()
ml_model.load_model()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': ml_model.model_version
    }), 200

@app.route('/readiness', methods=['GET'])
def readiness_check():
    """Readiness check endpoint"""
    try:
        # Check if model is loaded
        if ml_model.model is None:
            return jsonify({
                'status': 'not_ready',
                'message': 'Model not loaded'
            }), 503
        
        return jsonify({
            'status': 'ready',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return jsonify({
            'status': 'not_ready',
            'message': str(e)
        }), 503

@app.route('/predict', methods=['POST'])
def predict():
    """Prediction endpoint"""
    try:
        data = request.get_json()
        
        if 'features' not in data:
            return jsonify({'error': 'Features not provided'}), 400
        
        features = data['features']
        
        # Validate input
        if not isinstance(features, list) or len(features) != 20:
            return jsonify({'error': 'Features must be a list of 20 numbers'}), 400
        
        # Make prediction
        result = ml_model.predict(features)
        
        logger.info(f"Prediction made: {result['prediction']}")
        
        return jsonify({
            'success': True,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    """Metrics endpoint for monitoring"""
    return jsonify({
        'model_version': ml_model.model_version,
        'status': 'active',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/retrain', methods=['POST'])
def retrain():
    """Retrain model endpoint"""
    try:
        logger.info("Retraining model...")
        accuracy = ml_model.train_model()
        
        return jsonify({
            'success': True,
            'message': 'Model retrained successfully',
            'accuracy': accuracy,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Retraining error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False) 