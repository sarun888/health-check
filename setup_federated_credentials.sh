#!/bin/bash

# Setup Federated Credentials for GitHub Actions OIDC
# This fixes the AADSTS70025 error: no configured federated identity credentials

set -e

echo "🔐 Setting up Federated Credentials for GitHub Actions OIDC"
echo "This will fix the AADSTS70025 error you're seeing in GitHub Actions"
echo ""

# Configuration
SUBSCRIPTION_ID="6ab08646-8f78-4187-ac87-c762aa843c9b"
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

# Function to create federated credential
create_federated_credential() {
    local entity_type=$1
    local entity_name=$2
    local credential_name=$3
    
    echo "📝 Creating federated credential: $credential_name"
    echo "   Subject: repo:$REPO_OWNER/$REPO_NAME:$entity_type:$entity_name"
    
    # Create the federated credential
    az ad app federated-credential create \
        --id $CLIENT_ID \
        --parameters '{
            "name": "'$credential_name'",
            "issuer": "https://token.actions.githubusercontent.com",
            "subject": "repo:'$REPO_OWNER'/'$REPO_NAME':'$entity_type':'$entity_name'",
            "description": "GitHub Actions OIDC for '$entity_name'",
            "audiences": ["api://AzureADTokenExchange"]
        }' 2>/dev/null && echo "   ✅ Created: $credential_name" || echo "   ⚠️  Already exists or failed: $credential_name"
}

echo "🌍 Creating federated credentials for GitHub Actions..."

# Create federated credentials for different scenarios that GitHub Actions uses
create_federated_credential "environment" "development" "github-actions-dev"
create_federated_credential "environment" "staging" "github-actions-staging"
create_federated_credential "environment" "production" "github-actions-prod"

# For branch-based deployments
create_federated_credential "ref" "refs/heads/main" "github-actions-main"
create_federated_credential "ref" "refs/heads/develop" "github-actions-develop"

# For pull requests (if needed)
create_federated_credential "pull_request" "" "github-actions-pr"

echo ""
echo "🔍 Verifying created federated credentials..."
echo "Current federated credentials for $APP_NAME:"
az ad app federated-credential list \
    --id $CLIENT_ID \
    --query "[].{Name:name,Subject:subject,Issuer:issuer}" \
    --output table

echo ""
echo "🎉 Federated Credentials Setup Complete!"
echo ""
echo "📋 Your GitHub Repository Secrets should be:"
echo "   AZURE_CLIENT_ID: $CLIENT_ID"
echo "   AZURE_TENANT_ID: $TENANT_ID"
echo ""
echo "🚀 Next Steps:"
echo "1. Verify these secrets are set in GitHub:"
echo "   https://github.com/$REPO_OWNER/$REPO_NAME/settings/secrets/actions"
echo ""
echo "2. Create GitHub environments (if not already created):"
echo "   - development"
echo "   - staging"
echo "   - production"
echo ""
echo "3. Re-run your GitHub Actions workflow - the OIDC authentication should now work!"
echo ""
echo "🔧 The AADSTS70025 error should now be resolved." 