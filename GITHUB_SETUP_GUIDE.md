# GitHub Actions Setup Guide

Since you've already configured the Azure permissions, here's your complete guide to finish the setup and resolve the ACR access denied error.

## 🔐 Step 1: Get Your Azure App Registration Details

First, you need to get your Azure App Registration details. Run this command in your terminal:

```bash
# Login to Azure if not already logged in
az login

# Set your subscription
az account set --subscription "6ab08646-8f78-4187-ac87-c762aa843c9b"

# Get your App Registration details
az ad app list --display-name "InstantStagingAKSCluster" --query "[0].{ClientId:appId,DisplayName:displayName}" -o table

# Get your Tenant ID
az account show --query tenantId -o tsv
```

**Save these values - you'll need them for GitHub secrets:**
- `CLIENT_ID` (from the first command)
- `TENANT_ID` (from the second command)

## 🔑 Step 2: Configure GitHub Repository Secrets

1. **Go to your GitHub repository**: https://github.com/sarun888/health-check

2. **Navigate to Settings**:
   - Click on **Settings** tab
   - Go to **Secrets and variables** → **Actions**

3. **Add Repository Secrets**:
   Click **New repository secret** and add these two secrets:

   | Secret Name | Value | Description |
   |-------------|-------|-------------|
   | `AZURE_CLIENT_ID` | `<your-client-id-from-step-1>` | Azure App Registration Client ID |
   | `AZURE_TENANT_ID` | `<your-tenant-id-from-step-1>` | Azure Tenant ID |

   **Example:**
   ```
   AZURE_CLIENT_ID: 12345678-1234-1234-1234-123456789012
   AZURE_TENANT_ID: 87654321-4321-4321-4321-210987654321
   ```

## 🌍 Step 3: Create GitHub Environments

1. **In your GitHub repository, go to Settings**

2. **Click on "Environments"** (in the left sidebar)

3. **Create these three environments**:

   ### Development Environment
   - Click **New environment**
   - Name: `development`
   - Protection rules: None (leave default)
   - Click **Configure environment**

   ### Staging Environment
   - Click **New environment**
   - Name: `staging`
   - Protection rules: 
     - ✅ Required reviewers: Add 1 reviewer
     - ✅ Wait timer: 0 minutes
   - Click **Configure environment**

   ### Production Environment
   - Click **New environment**
   - Name: `production`
   - Protection rules:
     - ✅ Required reviewers: Add 1-2 reviewers
     - ✅ Deployment branches: Select "Selected branches" → Add rule: `main`
     - ✅ Wait timer: 5 minutes (optional)
   - Click **Configure environment**

## ✅ Step 4: Verify Azure Permissions

Let's verify your service principal has the correct permissions:

```bash
# Get your Client ID
CLIENT_ID=$(az ad app list --display-name "InstantStagingAKSCluster" --query "[0].appId" -o tsv)

# Check role assignments
echo "Current role assignments:"
az role assignment list --assignee $CLIENT_ID --all --query "[].{Role:roleDefinitionName,Scope:scope}" -o table

# Test ACR access
echo "Testing ACR access..."
az acr login --name aksinstant
```

**Expected roles you should see:**
- `AcrPush` on the ACR resource (`/subscriptions/.../aksinstant`)
- `Reader` on the resource group (`/subscriptions/.../resourceGroups/mlmodel`)

## 🚀 Step 5: Test the Workflow

1. **Go to the Actions tab** in your GitHub repository

2. **Find the workflow**: "Deploy ML Health Check to Azure ML Studio"

3. **Click "Run workflow"**:
   - Use workflow from: `main`
   - Deployment environment: `dev`
   - Click **Run workflow**

4. **Monitor the workflow**:
   - Click on the running workflow
   - Watch the "Build & Push Container" job
   - The ACR login should now succeed

## 🔧 Step 6: Troubleshooting Common Issues

### Issue 1: "DefaultAzureCredential failed to retrieve a token"
**Solution:**
- Double-check GitHub secrets are exactly: `AZURE_CLIENT_ID` and `AZURE_TENANT_ID`
- Verify the values don't have extra spaces or characters
- Wait 5-10 minutes after creating secrets

### Issue 2: Still getting "denied: requested access to the resource is denied"
**Solution:**
```bash
# Re-assign ACR permissions
CLIENT_ID=$(az ad app list --display-name "InstantStagingAKSCluster" --query "[0].appId" -o tsv)

# Assign AcrPush role
az role assignment create \
  --assignee $CLIENT_ID \
  --role "AcrPush" \
  --scope "/subscriptions/6ab08646-8f78-4187-ac87-c762aa843c9b/resourceGroups/mlmodel/providers/Microsoft.ContainerRegistry/registries/aksinstant"

# Assign Reader role on resource group
az role assignment create \
  --assignee $CLIENT_ID \
  --role "Reader" \
  --scope "/subscriptions/6ab08646-8f78-4187-ac87-c762aa843c9b/resourceGroups/mlmodel"
```

### Issue 3: OIDC Authentication Issues
**Solution:**
```bash
# Create/update federated credentials
CLIENT_ID=$(az ad app list --display-name "InstantStagingAKSCluster" --query "[0].appId" -o tsv)

# For main branch pushes
az ad app federated-credential create \
  --id $CLIENT_ID \
  --parameters '{
    "name": "github-actions-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:sarun888/health-check:ref:refs/heads/main",
    "description": "GitHub Actions for main branch",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# For environments
az ad app federated-credential create \
  --id $CLIENT_ID \
  --parameters '{
    "name": "github-actions-dev",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:sarun888/health-check:environment:development",
    "description": "GitHub Actions for development environment",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### Issue 4: GitHub Environment Not Found
**Solution:**
- Ensure environment names are exactly: `development`, `staging`, `production`
- Check spelling and case sensitivity
- Environments must be created in GitHub repository settings

## 📊 Step 7: Verify Success

After running the workflow successfully, you should see:

1. **In the workflow logs**:
   ```
   ✅ Successfully authenticated to Azure
   ✅ ACR login successful
   ✅ Docker image built and pushed
   ```

2. **In Azure Container Registry**:
   - Go to Azure Portal → Container Registry → aksinstant
   - Check "Repositories" → You should see `ml-health-check` with your image

3. **ACR Repository URL**: `aksinstant.azurecr.io/ml-health-check:latest`

## 🎯 Quick Verification Commands

Run these to verify everything is working:

```bash
# 1. Check Azure login
az account show

# 2. Check ACR access
az acr login --name aksinstant

# 3. List repositories in ACR
az acr repository list --name aksinstant --output table

# 4. Check your app registration
az ad app list --display-name "InstantStagingAKSCluster" --query "[0].{ClientId:appId,DisplayName:displayName}" -o table
```

## 📞 Need Help?

If you're still having issues:

1. **Check the workflow logs** for specific error messages
2. **Verify GitHub secrets** are set correctly
3. **Ensure environments** are created with exact names
4. **Wait 5-10 minutes** after making changes for Azure permissions to propagate
5. **Re-run the workflow** after making changes

The key change we made was switching from Client Secret authentication to OIDC (Workload Identity Federation), which is more secure and doesn't require managing secrets in Azure. 