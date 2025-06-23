import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }), 200

@app.route("/readiness", methods=["GET"])
def readiness():
    return jsonify({
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route("/score", methods=["POST"])
def score():
    try:
        data = request.get_json()
        
        # Simple mock prediction
        if 'data' in data and isinstance(data['data'], list):
            predictions = []
            for row in data['data']:
                if isinstance(row, list) and len(row) >= 1:
                    # Mock prediction based on first feature
                    pred = 1 if row[0] > 0 else 0
                    prob = [0.3, 0.7] if pred == 1 else [0.7, 0.3]
                    predictions.append({
                        "prediction": pred,
                        "probabilities": prob,
                        "model_version": "1.0.0"
                    })
                else:
                    predictions.append({"error": "Invalid row format"})
            return jsonify(predictions), 200
        
        elif 'features' in data and isinstance(data['features'], list):
            # Single prediction
            features = data['features']
            if len(features) >= 1:
                pred = 1 if features[0] > 0 else 0
                prob = [0.3, 0.7] if pred == 1 else [0.7, 0.3]
                return jsonify({
                    "prediction": pred,
                    "probabilities": prob,
                    "model_version": "1.0.0"
                }), 200
            else:
                return jsonify({"error": "Need at least 1 feature"}), 400
        
        else:
            return jsonify({"error": "Invalid input format. Use 'data' or 'features'."}), 400
            
    except Exception as e:
        logger.exception("Error in /score:")
        return jsonify({
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "message": "ML Health Check API",
        "version": "1.0.0",
        "endpoints": ["/health", "/readiness", "/score"]
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False) 