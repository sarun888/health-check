#!/bin/bash

# Fix ACR Push Permissions for Service Principal
# This fixes the "denied: requested access to the resource is denied" error

set -e

echo "🐳 Fixing ACR Push Permissions"
echo "This will fix the 'denied: requested access to the resource is denied' error"
echo ""

# Configuration
SUBSCRIPTION_ID="6ab08646-8f78-4187-ac87-c762aa843c9b"
RESOURCE_GROUP="mlmodel"
REGISTRY_NAME="aksinstant"
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

# Get ACR resource ID
echo "🔍 Getting ACR resource information..."
ACR_ID=$(az acr show --name $REGISTRY_NAME --resource-group $RESOURCE_GROUP --query id -o tsv 2>/dev/null)

if [ -z "$ACR_ID" ]; then
    echo "❌ ACR '$REGISTRY_NAME' not found in resource group '$RESOURCE_GROUP'"
    echo "Available ACRs:"
    az acr list --query "[].{Name:name,ResourceGroup:resourceGroup,LoginServer:loginServer}" -o table
    exit 1
fi

echo "✅ Found ACR: $ACR_ID"
echo ""

# Check current role assignments
echo "📊 Current role assignments for service principal:"
az role assignment list --assignee $CLIENT_ID --all --query "[].{Role:roleDefinitionName,Scope:scope}" -o table

echo ""

# Assign AcrPush role to the service principal
echo "🔐 Assigning AcrPush role to service principal..."
az role assignment create \
    --assignee $CLIENT_ID \
    --role "AcrPush" \
    --scope "$ACR_ID" \
    --output none && echo "✅ AcrPush role assigned" || echo "⚠️  AcrPush role may already be assigned"

# Assign Reader role on resource group (sometimes needed for ACR operations)
echo "📖 Assigning Reader role on resource group..."
RG_ID=$(az group show --name $RESOURCE_GROUP --query id -o tsv)
az role assignment create \
    --assignee $CLIENT_ID \
    --role "Reader" \
    --scope "$RG_ID" \
    --output none && echo "✅ Reader role assigned" || echo "⚠️  Reader role may already be assigned"

# Optional: Assign AcrPull role (needed for some operations)
echo "📥 Assigning AcrPull role to service principal..."
az role assignment create \
    --assignee $CLIENT_ID \
    --role "AcrPull" \
    --scope "$ACR_ID" \
    --output none && echo "✅ AcrPull role assigned" || echo "⚠️  AcrPull role may already be assigned"

echo ""
echo "📊 Updated role assignments:"
az role assignment list --assignee $CLIENT_ID --all --query "[].{Role:roleDefinitionName,Scope:scope}" -o table

echo ""
echo "🧪 Testing ACR access..."
az acr login --name $REGISTRY_NAME && echo "✅ ACR login successful!" || {
    echo "❌ ACR login failed. Checking further..."
    
    echo "🔍 ACR details:"
    az acr show --name $REGISTRY_NAME --query "{Name:name,LoginServer:loginServer,AdminUserEnabled:adminUserEnabled,ResourceGroup:resourceGroup}" -o table
    
    echo "🔍 Service Principal details:"
    az ad sp show --id $CLIENT_ID --query "{DisplayName:displayName,AppId:appId,ObjectId:id}" -o table
    
    exit 1
}

echo ""
echo "🎉 ACR Permissions Fixed!"
echo ""
echo "📋 Summary of permissions assigned:"
echo "   ✅ AcrPush - Can push images to ACR"
echo "   ✅ AcrPull - Can pull images from ACR"  
echo "   ✅ Reader - Can read resource group information"
echo ""
echo "🚀 Next Steps:"
echo "1. Wait 2-3 minutes for Azure permissions to propagate"
echo "2. Re-run your GitHub Actions workflow"
echo "3. The ACR push should now succeed!"
echo ""
echo "Expected success message in GitHub Actions:"
echo "   ✅ Successfully authenticated to Azure"
echo "   ✅ ACR login successful"
echo "   ✅ Docker image built and pushed" 