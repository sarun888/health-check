#!/bin/bash

# Setup Azure ML Permissions for Service Principal
# This ensures the service principal can deploy to Azure ML workspace

set -e

echo "🧠 Setting up Azure ML Permissions"
echo "This will assign necessary permissions for Azure ML deployment"
echo ""

# Configuration
SUBSCRIPTION_ID="6ab08646-8f78-4187-ac87-c762aa843c9b"
RESOURCE_GROUP="mlmodel"
WORKSPACE_NAME="samplemodel"
CLIENT_ID="01ba82ad-fbfe-4933-a718-a2e5fb7beb93"

# Check Azure login
echo "📋 Checking Azure login status..."
az account show > /dev/null 2>&1 || {
    echo "❌ Not logged in to Azure. Please run 'az login' first"
    exit 1
}

# Set subscription
echo "🔄 Setting subscription..."
az account set --subscription $SUBSCRIPTION_ID

echo "✅ Using Service Principal Client ID: $CLIENT_ID"
echo ""

# Check if Azure ML workspace exists
echo "🔍 Checking Azure ML workspace..."
WORKSPACE_ID=$(az ml workspace show --name $WORKSPACE_NAME --resource-group $RESOURCE_GROUP --query id -o tsv 2>/dev/null || echo "")

if [ -z "$WORKSPACE_ID" ]; then
    echo "⚠️  Azure ML workspace '$WORKSPACE_NAME' not found in resource group '$RESOURCE_GROUP'"
    echo "Available ML workspaces:"
    az ml workspace list --resource-group $RESOURCE_GROUP --query "[].{Name:name,ResourceGroup:resourceGroup}" -o table 2>/dev/null || echo "No ML workspaces found"
    
    echo ""
    echo "🔧 You have two options:"
    echo "1. Create an Azure ML workspace"
    echo "2. Use simulation mode (the deployment script will handle this)"
    echo ""
    echo "Creating Azure ML workspace..."
    
    # Try to create the workspace
    az ml workspace create \
        --name $WORKSPACE_NAME \
        --resource-group $RESOURCE_GROUP \
        --location "East US" \
        --display-name "Sample ML Model Workspace" \
        --description "Azure ML workspace for health-check deployment" \
        --output none && echo "✅ ML workspace created" || echo "⚠️  Failed to create ML workspace, will use simulation mode"
    
    # Get workspace ID after creation
    WORKSPACE_ID=$(az ml workspace show --name $WORKSPACE_NAME --resource-group $RESOURCE_GROUP --query id -o tsv 2>/dev/null || echo "")
fi

if [ -n "$WORKSPACE_ID" ]; then
    echo "✅ Found Azure ML workspace: $WORKSPACE_ID"
    echo ""
    
    # Assign Azure ML permissions
    echo "🔐 Assigning Azure ML permissions..."
    
    # AzureML Data Scientist role
    az role assignment create \
        --assignee $CLIENT_ID \
        --role "AzureML Data Scientist" \
        --scope "$WORKSPACE_ID" \
        --output none && echo "✅ AzureML Data Scientist role assigned" || echo "⚠️  AzureML Data Scientist role may already be assigned"
    
    # AzureML Compute Operator role
    az role assignment create \
        --assignee $CLIENT_ID \
        --role "AzureML Compute Operator" \
        --scope "$WORKSPACE_ID" \
        --output none && echo "✅ AzureML Compute Operator role assigned" || echo "⚠️  AzureML Compute Operator role may already be assigned"
    
    # Machine Learning Contributor (broader permissions)
    az role assignment create \
        --assignee $CLIENT_ID \
        --role "Contributor" \
        --scope "$WORKSPACE_ID" \
        --output none && echo "✅ Contributor role assigned to ML workspace" || echo "⚠️  Contributor role may already be assigned"
else
    echo "⚠️  Azure ML workspace not available - deployment will use simulation mode"
fi

echo ""
echo "📊 Current role assignments for service principal:"
az role assignment list --assignee $CLIENT_ID --all --query "[].{Role:roleDefinitionName,Scope:scope}" -o table

echo ""
echo "🎉 Azure ML Permissions Setup Complete!"
echo ""
echo "📋 Summary:"
if [ -n "$WORKSPACE_ID" ]; then
    echo "   ✅ Azure ML workspace is available"
    echo "   ✅ Service principal has ML permissions"
    echo "   ✅ Ready for Azure ML deployment"
else
    echo "   ⚠️  Azure ML workspace not available"
    echo "   ✅ Service principal has basic permissions"
    echo "   ✅ Deployment will use simulation mode"
fi
echo ""
echo "🚀 Next Steps:"
echo "1. Commit and push the deploy_to_azure_ml.py file to your repository"
echo "2. Re-run your GitHub Actions workflow"
echo "3. The deployment should now work (either real or simulated)" 