# 🚀 Quick Setup Guide - Static Configuration

This is a simplified setup guide using static configuration values instead of GitHub secrets.

## ⚠️ Important Note
This approach uses hardcoded values for simplicity. For production use, you should use GitHub secrets and environment variables for security.

## 📝 Setup Steps

### 1. Update Configuration Values

Edit the following files with your actual Azure values:

#### In `.github/workflows/deploy-to-azure-ml.yml`:
```yaml
env:
  # UPDATE THESE VALUES WITH YOUR AZURE INFORMATION
  SUBSCRIPTION_ID: 'your-subscription-id-here'
  RESOURCE_GROUP_DEV: 'rg-ml-health-check-dev'
  RESOURCE_GROUP_STAGING: 'rg-ml-health-check-staging' 
  RESOURCE_GROUP_PROD: 'rg-ml-health-check-prod'
  WORKSPACE_NAME_DEV: 'mlws-health-check-dev'
  WORKSPACE_NAME_STAGING: 'mlws-health-check-staging'
  WORKSPACE_NAME_PROD: 'mlws-health-check-prod'
  REGISTRY_LOGIN_SERVER: 'acrmlhealthcheck.azurecr.io'
```

#### In `deploy_to_azure_ml.py`:
```python
STATIC_CONFIG = {
    # UPDATE THESE VALUES WITH YOUR AZURE INFORMATION
    "SUBSCRIPTION_ID": "your-subscription-id-here",
    
    "DEV": {
        "RESOURCE_GROUP": "rg-ml-health-check-dev",
        "WORKSPACE_NAME": "mlws-health-check-dev",
        "REGISTRY_LOGIN_SERVER": "acrmlhealthcheck.azurecr.io",
        "IMAGE_URI": "acrmlhealthcheck.azurecr.io/ml-health-check:latest"
    },
    # ... (similar for STAGING and PRODUCTION)
}
```

### 2. Create Azure Resources

```bash
# Set your variables
SUBSCRIPTION_ID="your-subscription-id"
RESOURCE_GROUP="rg-ml-health-check-dev"
LOCATION="eastus"
ACR_NAME="acrmlhealthcheck"
WORKSPACE_NAME="mlws-health-check-dev"

# Login to Azure
az login

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Standard

# Create Azure ML Workspace
az ml workspace create --resource-group $RESOURCE_GROUP --name $WORKSPACE_NAME
```

### 3. Local Testing

```bash
# Test your app locally first
cd /mnt/c/Azure/health-check
source venv/bin/activate
python3 app.py
```

### 4. Manual Deployment Test

```bash
# Set environment for development
export ENVIRONMENT=development

# Run deployment script locally
python3 deploy_to_azure_ml.py
```

### 5. GitHub Actions Setup

1. Push your code to GitHub
2. The workflow will run automatically on push to `main` or `develop`
3. Or trigger manually using workflow dispatch

## 🔍 Testing Endpoints

Once deployed, test your endpoints:

```bash
# Health check
curl https://your-endpoint-uri/health

# Readiness check  
curl https://your-endpoint-uri/readiness

# Prediction
curl -X POST https://your-endpoint-uri/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]}'
```

## 🛠️ Troubleshooting

### Common Issues:

1. **Azure Authentication**: Make sure you're logged in with `az login`
2. **Resource Names**: Ensure your Azure resource names match the configuration
3. **Permissions**: Your account needs Contributor access to the resource groups
4. **Container Registry**: Make sure ACR exists and is accessible

### Getting Your Azure Values:

```bash
# Get subscription ID
az account show --query id -o tsv

# List resource groups
az group list --query "[].name" -o table

# List ML workspaces
az ml workspace list -o table
```

## 🔄 Migration to Secrets Later

When ready for production, you can migrate to using GitHub secrets by:

1. Adding secrets to your GitHub repository
2. Reverting the workflow to use `${{ secrets.SECRET_NAME }}`
3. Removing hardcoded values from the deployment script

This static approach is perfect for development and testing! 🚀 