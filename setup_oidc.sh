#!/bin/bash

# Azure OIDC Setup Script for GitHub Actions
# Repository: sarun888/health-check
# App Registration: InstantStagingAKSCluster

set -e

echo "🔐 Setting up OIDC Federated Credentials for GitHub Actions"
echo "Repository: sarun888/health-check"
echo "App Registration: InstantStagingAKSCluster"
echo ""

# Login to Azure
echo "📋 Checking Azure login status..."
az account show > /dev/null 2>&1 || {
    echo "❌ Not logged in to Azure. Please run 'az login' first"
    exit 1
}

# Get app registration details
echo "🔍 Finding App Registration..."
CLIENT_ID=$(az ad app list --display-name "InstantStagingAKSCluster" --query "[0].appId" -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

if [ -z "$CLIENT_ID" ]; then
    echo "❌ App Registration 'InstantStagingAKSCluster' not found"
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
    
    # Create the federated credential
    az ad app federated-credential create \
        --id $CLIENT_ID \
        --parameters '{
            "name": "'$credential_name'",
            "issuer": "https://token.actions.githubusercontent.com",
            "subject": "repo:sarun888/health-check:'$entity_type':'$entity_name'",
            "description": "GitHub Actions for '$entity_name'",
            "audiences": ["api://AzureADTokenExchange"]
        }' > /dev/null 2>&1 && echo "   ✅ Created: $credential_name" || echo "   ⚠️  Already exists or failed: $credential_name"
}

# Create federated credentials for environments
echo "🌍 Creating federated credentials for environments..."
create_federated_credential "environment" "development" "github-actions-dev"
create_federated_credential "environment" "staging" "github-actions-staging"
create_federated_credential "environment" "production" "github-actions-prod"

# Create federated credential for main branch (for build jobs)
echo "🌲 Creating federated credential for main branch..."
create_federated_credential "ref" "refs/heads/main" "github-actions-main"

# Create federated credential for develop branch (if needed)
echo "🌿 Creating federated credential for develop branch..."
create_federated_credential "ref" "refs/heads/develop" "github-actions-develop"

echo ""
echo "🎉 OIDC Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Add these GitHub Repository Secrets:"
echo "   AZURE_CLIENT_ID: $CLIENT_ID"
echo "   AZURE_TENANT_ID: $TENANT_ID"
echo ""
echo "2. Make sure your GitHub repository has these environments:"
echo "   - development"
echo "   - staging"
echo "   - production"
echo ""
echo "3. Test the workflow by running it manually"
echo ""
echo "🔗 GitHub Settings URL:"
echo "   https://github.com/sarun888/health-check/settings/secrets/actions" 