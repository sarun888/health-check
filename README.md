# ML Model API - Azure DevOps Pipeline

A production-ready machine learning model deployment pipeline using Azure services, Docker, and GitHub Actions.

## Architecture Overview

This project implements a complete MLOps pipeline with the following components:

- **ML Model**: Random Forest classifier served via Flask API
- **Containerization**: Multi-stage Docker build with security best practices
- **CI/CD**: GitHub Actions workflow with automated testing and deployment
- **Azure Services**:
  - Azure Container Registry (ACR) for container images
  - Azure ML Studio for model management and deployment
  - Azure Container Instances for staging/testing
  - Azure Key Vault for secrets management
  - Application Insights for monitoring
  - Log Analytics for centralized logging

## Project Structure

```
ML-Model/
├── app.py                      # Flask ML API application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Multi-stage container build
├── gunicorn_config.py         # Production WSGI configuration
├── deploy_to_azure_ml.py      # Azure ML deployment script
├── tests/
│   └── test_app.py            # Comprehensive test suite
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # GitHub Actions CI/CD pipeline
└── terraform/                 # Infrastructure as Code
    ├── main.tf                # Main Terraform configuration
    ├── variables.tf           # Variable definitions
    ├── locals.tf              # Local values and configuration
    └── outputs.tf             # Output values
```

## Prerequisites

- Azure subscription with appropriate permissions
- GitHub repository with Actions enabled
- Terraform >= 1.0
- Docker Desktop
- Python 3.11+

## Quick Start

### 1. Deploy Infrastructure

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="project_name=yourproject"

# Apply infrastructure
terraform apply -var="project_name=yourproject"
```

### 2. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

```
AZURE_CREDENTIALS          # Service principal JSON
AZURE_SUBSCRIPTION_ID       # Azure subscription ID
AZURE_CONTAINER_REGISTRY    # ACR login server
AZURE_RESOURCE_GROUP        # Resource group name
AZURE_ML_WORKSPACE         # ML workspace name
AZURE_KEY_VAULT_URL        # Key Vault URL
AZURE_CLIENT_ID            # Service principal client ID
AZURE_CLIENT_SECRET        # Service principal secret
```

### 3. Trigger Deployment

Push code to the `main` branch to trigger the CI/CD pipeline:

```bash
git add .
git commit -m "Initial deployment"
git push origin main
```

## API Endpoints

### Health Check
```bash
GET /health
```
Returns service health status.

### Readiness Check
```bash
GET /readiness
```
Returns service readiness for traffic.

### Make Prediction
```bash
POST /predict
Content-Type: application/json

{
  "features": [0.1, 0.2, 0.3, ..., 2.0]  # 20 numeric features
}
```

### Get Metrics
```bash
GET /metrics
```
Returns service metrics for monitoring.

### Retrain Model
```bash
POST /retrain
```
Triggers model retraining.

## Local Development

### Run with Python
```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python app.py
```

### Run with Docker
```bash
# Build image
docker build -t ml-model-api .

# Run container
docker run -p 8080:8080 ml-model-api
```

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v --cov=.
```

## Deployment Options

### Option 1: Azure ML Studio (Recommended)
- Managed online endpoints
- Built-in monitoring and logging
- Automatic scaling
- A/B testing capabilities

### Option 2: Azure Container Instances
- Quick staging deployments
- Cost-effective for low traffic
- Easy integration with CI/CD

### Option 3: Azure Kubernetes Service
- High availability and scalability
- Advanced networking features
- Custom configurations

## Monitoring and Observability

### Application Insights
- Request/response tracking
- Dependency monitoring
- Custom metrics and events
- Performance counters

### Log Analytics
- Centralized log aggregation
- Custom queries with KQL
- Alerting and dashboards
- Long-term retention

### Health Checks
- Kubernetes-style probes
- Load balancer integration
- Automatic failover

## Security Features

### Container Security
- Non-root user execution
- Multi-stage builds
- Minimal base images
- Security scanning with Trivy

### Azure Security
- Managed identities
- Key Vault integration
- Network ACLs
- HTTPS enforcement

### CI/CD Security
- No hardcoded secrets
- Vulnerability scanning
- Code quality checks
- Dependency auditing

## Production Considerations

### Scaling
- Horizontal pod autoscaling
- Azure ML endpoint scaling
- Load balancing configuration

### Cost Optimization
- Spot instances for training
- Reserved capacity for production
- Automatic resource cleanup

### Disaster Recovery
- Multi-region deployment
- Backup strategies
- Failover procedures

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `production` |
| `PORT` | Server port | `8080` |
| `AZURE_KEY_VAULT_URL` | Key Vault URL | None |

## Troubleshooting

### Common Issues

1. **Model Not Loading**: Check file permissions and model path
2. **Authentication Errors**: Verify Azure credentials and permissions
3. **Container Build Failures**: Check Dockerfile syntax and dependencies
4. **Deployment Timeout**: Increase timeout values in CI/CD pipeline

### Debug Commands

```bash
# Check container logs
docker logs <container-id>

# Test endpoint locally
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [0.1, 0.2, ...]}'

# Check Azure ML endpoint
az ml online-endpoint show -n ml-model-endpoint
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run linting and tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Contact the DevOps team
- Check Azure documentation

---

**Note**: This is a reference implementation. Customize according to your specific requirements and security policies. # health-check
# health-check
# health-check
# health-check
