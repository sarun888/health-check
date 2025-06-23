#!/bin/bash

# Fix ACR Permissions and Setup OIDC for GitHub Actions
# This script ensures proper Azure Container Registry access for CI/CD pipeline

set -e

echo "🔧 Fixing ACR Permissions and OIDC Setup"
echo "Repository: sarun888/health-check"
echo "Registry: aksinstant.azurecr.io"
echo ""

# Configuration
SUBSCRIPTION_ID="6ab08646-8f78-4187-ac87-c762aa843c9b"
RESOURCE_GROUP="mlmodel"
REGISTRY_NAME="aksinstant"
APP_NAME="InstantStagingAKSCluster"
REPO_OWNER="sarun888"
REPO_NAME="health-check"

# Check Azure login
echo "📋 Checking Azure login status..."
az account show > /dev/null 2>&1 || {
    echo "❌ Not logged in to Azure. Please run 'az login' first"
    exit 1
}

# Set subscription
echo "🔄 Setting subscription..."
az account set --subscription $SUBSCRIPTION_ID

# Get app registration details
echo "🔍 Finding App Registration..."
CLIENT_ID=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

if [ -z "$CLIENT_ID" ]; then
    echo "❌ App Registration '$APP_NAME' not found"
    echo "Available app registrations:"
    az ad app list --query "[].displayName" -o table
    exit 1
fi

echo "✅ Found App Registration:"
echo "   Client ID: $CLIENT_ID"
echo "   Tenant ID: $TENANT_ID"
echo ""

# Create service principal if it doesn't exist
echo "👤 Ensuring Service Principal exists..."
SP_EXISTS=$(az ad sp list --display-name "$APP_NAME" --query "[0].appId" -o tsv)
if [ -z "$SP_EXISTS" ]; then
    echo "Creating service principal..."
    az ad sp create --id $CLIENT_ID
    echo "✅ Service principal created"
else
    echo "✅ Service principal already exists"
fi

# Assign ACR permissions
echo "🐳 Assigning ACR permissions..."

# Get ACR resource ID
ACR_ID=$(az acr show --name $REGISTRY_NAME --resource-group $RESOURCE_GROUP --query id -o tsv)

if [ -z "$ACR_ID" ]; then
    echo "❌ ACR '$REGISTRY_NAME' not found in resource group '$RESOURCE_GROUP'"
    exit 1
fi

# Assign AcrPush role
echo "Assigning AcrPush role to service principal..."
az role assignment create \
    --assignee $CLIENT_ID \
    --role "AcrPush" \
    --scope "$ACR_ID" \
    --output none || echo "   ⚠️  AcrPush role may already be assigned"

# Assign Reader role on resource group (needed for ACR access)
RG_ID=$(az group show --name $RESOURCE_GROUP --query id -o tsv)
echo "Assigning Reader role on resource group..."
az role assignment create \
    --assignee $CLIENT_ID \
    --role "Reader" \
    --scope "$RG_ID" \
    --output none || echo "   ⚠️  Reader role may already be assigned"

echo "✅ ACR permissions assigned"

# Create OIDC federated credentials
echo "🔐 Setting up OIDC federated credentials..."

create_federated_credential() {
    local entity_type=$1
    local entity_name=$2
    local credential_name=$3
    
    echo "Creating federated credential: $credential_name"
    
    az ad app federated-credential create \
        --id $CLIENT_ID \
        --parameters '{
            "name": "'$credential_name'",
            "issuer": "https://token.actions.githubusercontent.com",
            "subject": "repo:'$REPO_OWNER'/'$REPO_NAME':'$entity_type':'$entity_name'",
            "description": "GitHub Actions for '$entity_name'",
            "audiences": ["api://AzureADTokenExchange"]
        }' > /dev/null 2>&1 && echo "   ✅ Created: $credential_name" || echo "   ⚠️  Already exists: $credential_name"
}

# Create federated credentials for different scenarios
create_federated_credential "environment" "development" "github-actions-dev"
create_federated_credential "environment" "staging" "github-actions-staging"
create_federated_credential "environment" "production" "github-actions-prod"
create_federated_credential "ref" "refs/heads/main" "github-actions-main"
create_federated_credential "ref" "refs/heads/develop" "github-actions-develop"

# Test ACR access
echo ""
echo "🧪 Testing ACR access..."
echo "Attempting to login to ACR..."
az acr login --name $REGISTRY_NAME && echo "✅ ACR login successful" || {
    echo "❌ ACR login failed"
    echo "Checking current permissions..."
    az role assignment list --assignee $CLIENT_ID --all --query "[].{Role:roleDefinitionName,Scope:scope}" -o table
    exit 1
}

# Check current role assignments
echo ""
echo "📊 Current Role Assignments:"
az role assignment list --assignee $CLIENT_ID --all --query "[].{Role:roleDefinitionName,Scope:scope}" -o table

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "📋 GitHub Repository Secrets Required:"
echo "   AZURE_CLIENT_ID: $CLIENT_ID"
echo "   AZURE_TENANT_ID: $TENANT_ID"
echo ""
echo "🚀 Next Steps:"
echo "1. Add the secrets to your GitHub repository:"
echo "   https://github.com/$REPO_OWNER/$REPO_NAME/settings/secrets/actions"
echo ""
echo "2. Create GitHub environments if they don't exist:"
echo "   - development"
echo "   - staging"  
echo "   - production"
echo ""
echo "3. Test the workflow by running it manually"
echo ""
echo "🔧 Troubleshooting:"
echo "If you still get access denied errors:"
echo "1. Verify the GitHub secrets are correctly set"
echo "2. Check that the GitHub repository name matches: $REPO_OWNER/$REPO_NAME"
echo "3. Ensure GitHub environments are created and spelled correctly"
echo "4. Wait 5-10 minutes for Azure role assignments to propagate" 