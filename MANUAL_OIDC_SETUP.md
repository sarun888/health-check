# Manual OIDC Setup Guide - Azure Portal

## ❌ Current Error
You're seeing: `AADSTS70025: The client 'InstantStagingAKSCluster' has no configured federated identity credentials`

This means your Azure App Registration needs federated credentials configured for GitHub Actions OIDC.

## 🔧 Solution: Configure Federated Credentials

### Option 1: Using Azure CLI (Recommended - Fast)
```bash
# Run this script to automatically configure everything
./setup_federated_credentials.sh
```

### Option 2: Manual Setup via Azure Portal

#### Step 1: Find Your App Registration
1. Go to **Azure Portal** → **Azure Active Directory**
2. Click **App registrations**
3. Find and click **InstantStagingAKSCluster**

#### Step 2: Add Federated Credentials
1. In your App Registration, click **Certificates & secrets**
2. Click the **Federated credentials** tab
3. Click **Add credential**

#### Step 3: Configure Each Credential
You need to create **5 separate credentials** for different GitHub Actions scenarios:

##### Credential 1: Main Branch
- **Federated credential scenario**: GitHub Actions deploying Azure resources
- **Organization**: `sarun888`
- **Repository**: `health-check`
- **Entity type**: Branch
- **GitHub branch name**: `main`
- **Name**: `github-actions-main`
- **Description**: GitHub Actions for main branch

##### Credential 2: Development Environment
- **Federated credential scenario**: GitHub Actions deploying Azure resources
- **Organization**: `sarun888`
- **Repository**: `health-check`
- **Entity type**: Environment
- **GitHub environment name**: `development`
- **Name**: `github-actions-dev`
- **Description**: GitHub Actions for development environment

##### Credential 3: Staging Environment
- **Federated credential scenario**: GitHub Actions deploying Azure resources
- **Organization**: `sarun888`
- **Repository**: `health-check`
- **Entity type**: Environment
- **GitHub environment name**: `staging`
- **Name**: `github-actions-staging`
- **Description**: GitHub Actions for staging environment

##### Credential 4: Production Environment
- **Federated credential scenario**: GitHub Actions deploying Azure resources
- **Organization**: `sarun888`
- **Repository**: `health-check`
- **Entity type**: Environment
- **GitHub environment name**: `production`
- **Name**: `github-actions-prod`
- **Description**: GitHub Actions for production environment

##### Credential 5: Develop Branch
- **Federated credential scenario**: GitHub Actions deploying Azure resources
- **Organization**: `sarun888`
- **Repository**: `health-check`
- **Entity type**: Branch
- **GitHub branch name**: `develop`
- **Name**: `github-actions-develop`
- **Description**: GitHub Actions for develop branch

#### Step 4: Verify Configuration
After creating all credentials, you should see 5 federated credentials listed:
- `github-actions-main`
- `github-actions-dev`
- `github-actions-staging`
- `github-actions-prod`
- `github-actions-develop`

## 📋 GitHub Secrets Required

Make sure you have these secrets in your GitHub repository:

1. Go to: https://github.com/sarun888/health-check/settings/secrets/actions
2. Add these secrets:

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `AZURE_CLIENT_ID` | Your App Registration Client ID | Azure Portal → App Registration → Overview → Application (client) ID |
| `AZURE_TENANT_ID` | Your Azure Tenant ID | Azure Portal → Azure Active Directory → Overview → Tenant ID |

## 🌍 GitHub Environments Required

Create these environments in GitHub:
1. Go to: https://github.com/sarun888/health-check/settings/environments
2. Create:
   - `development`
   - `staging`
   - `production`

## ✅ Test the Fix

1. **Re-run your GitHub Actions workflow**
2. **Monitor the "Azure Login (OIDC)" step**
3. **It should now succeed** instead of showing the AADSTS70025 error

## 🔍 Expected Success Log
After the fix, you should see:
```
✅ Successfully authenticated to Azure
✅ ACR login successful
✅ Docker image built and pushed
```

## 🚨 Common Issues After Setup

### Issue: Environment not found
**Error**: `No environment named 'development' found`
**Solution**: Create the GitHub environments exactly as listed above

### Issue: Still getting AADSTS70025
**Solution**: 
- Wait 5-10 minutes for Azure to propagate the changes
- Double-check the repository name is exactly `sarun888/health-check`
- Verify all 5 federated credentials were created

### Issue: Wrong repository name
**Error**: Token validation failed
**Solution**: Ensure the federated credentials use the exact repository name `sarun888/health-check` 