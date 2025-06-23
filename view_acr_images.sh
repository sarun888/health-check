#!/bin/bash

# View Docker Images in Azure Container Registry
# This script shows you all your pushed images

echo "🐳 Viewing Images in Azure Container Registry"
echo "Registry: aksinstant.azurecr.io"
echo ""

# Configuration
REGISTRY_NAME="aksinstant"
IMAGE_NAME="ml-health-check"

# Check Azure login
az account show > /dev/null 2>&1 || {
    echo "❌ Not logged in to Azure. Please run 'az login' first"
    exit 1
}

echo "📋 Container Registry Information:"
az acr show --name $REGISTRY_NAME --query "{Name:name,LoginServer:loginServer,ResourceGroup:resourceGroup,Location:location}" -o table

echo ""
echo "📦 All Repositories in ACR:"
az acr repository list --name $REGISTRY_NAME --output table

echo ""
echo "🏷️  All Tags for ml-health-check repository:"
az acr repository show-tags --name $REGISTRY_NAME --repository $IMAGE_NAME --output table

echo ""
echo "📊 Detailed Information for ml-health-check repository:"
az acr repository show --name $REGISTRY_NAME --repository $IMAGE_NAME

echo ""
echo "🔍 Recent Image Manifests:"
az acr repository show-manifests --name $REGISTRY_NAME --repository $IMAGE_NAME --query "[].{Tag:tags[0],Digest:digest,Created:timestamp,Size:imageSize}" --output table

echo ""
echo "🌐 Direct URLs to view in Azure Portal:"
echo "Registry Overview: https://portal.azure.com/#@/resource/subscriptions/6ab08646-8f78-4187-ac87-c762aa843c9b/resourceGroups/mlmodel/providers/Microsoft.ContainerRegistry/registries/aksinstant/overview"
echo "Repositories: https://portal.azure.com/#@/resource/subscriptions/6ab08646-8f78-4187-ac87-c762aa843c9b/resourceGroups/mlmodel/providers/Microsoft.ContainerRegistry/registries/aksinstant/repositories" 