import os
import logging
import joblib
from flask import Flask, request, jsonify
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class MLModel:
    def __init__(self):
        self.model = None
        self.model_version = "1.0.0"
        self.model_path = "models/model.pkl"  # Updated path

    def train_model(self):
        logger.info("Training new model...")
        X, y = make_classification(n_samples=1000, n_features=20, n_informative=10,
                                   n_redundant=10, random_state=42)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        joblib.dump(self.model, self.model_path)
        logger.info(f"Model trained with accuracy: {acc:.4f}")
        return acc

    def load_model(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            logger.info("Loaded model from disk.")
        else:
            logger.warning("Model not found. Training a new one...")
            self.train_model()

    def predict(self, features):
        if self.model is None:
            raise ValueError("Model not loaded")
        pred = self.model.predict([features])[0]
        prob = self.model.predict_proba([features])[0]
        return {
            "prediction": int(pred),
            "probabilities": prob.tolist(),
            "model_version": self.model_version
        }

# Initialize and load model
ml_model = MLModel()
ml_model.load_model()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": ml_model.model_version
    }), 200

@app.route("/readiness", methods=["GET"])
def readiness():
    return jsonify({
        "status": "ready" if ml_model.model else "not_ready",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route("/score", methods=["POST"])
def score():
    try:
        data = request.get_json()
        inputs = data.get("data") or data.get("features")

        if isinstance(inputs, list):
            if all(isinstance(row, list) for row in inputs):  # batch
                results = [ml_model.predict(row) for row in inputs]
                return jsonify(results), 200
            elif isinstance(inputs[0], (int, float)):  # single row
                return jsonify(ml_model.predict(inputs)), 200
        return jsonify({"error": "Invalid input format. Use 'data' or 'features'."}), 400

    except Exception as e:
        logger.exception("Error in /score:")
        return jsonify({
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        features = data.get("features", [])
        if not isinstance(features, list) or len(features) != 20:
            return jsonify({"error": "Expecting 'features': list of 20 numbers"}), 400
        result = ml_model.predict(features)
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.exception("Prediction failed")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route("/metrics", methods=["GET"])
def metrics():
    return jsonify({
        "model_version": ml_model.model_version,
        "status": "active",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route("/retrain", methods=["POST"])
def retrain():
    try:
        acc = ml_model.train_model()
        return jsonify({
            "success": True,
            "accuracy": acc,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.exception("Retraining failed")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # Updated for Azure ML
    app.run(host="0.0.0.0", port=port, debug=False)
