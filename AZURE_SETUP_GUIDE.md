# Azure ML CI/CD Setup Guide

This guide walks you through setting up secure Azure authentication for your ML deployment pipeline using modern DevOps best practices.

## 🔐 Authentication Methods

### Option 1: Workload Identity Federation (OIDC) - **RECOMMENDED**
Modern keyless authentication - most secure approach

### Option 2: Service Principal with Secrets - Fallback option

## 🚀 Setup Instructions

### Step 1: Create Azure App Registration

1. **Go to Azure Portal** → Azure Active Directory → App registrations
2. **Click "New registration"**
   - Name: `ml-health-check-ci-cd`
   - Account types: "Accounts in this organizational directory only"
   - Redirect URI: Leave empty
3. **Save the following values** (you'll need them later):
   - Application (client) ID
   - Directory (tenant) ID

### Step 2: Create Service Principal & Assign Permissions

```bash
# Login to Azure CLI
az login

# Set your subscription
az account set --subscription "6ab08646-8f78-4187-ac87-c762aa843c9b"

# Create service principal (if not created via portal)
az ad sp create --id <APPLICATION_CLIENT_ID>

# Assign ML workspace permissions
az role assignment create \
  --assignee <APPLICATION_CLIENT_ID> \
  --role "AzureML Compute Operator" \
  --scope "/subscriptions/6ab08646-8f78-4187-ac87-c762aa843c9b/resourceGroups/mlmodel/providers/Microsoft.MachineLearningServices/workspaces/samplemodel"

az role assignment create \
  --assignee <APPLICATION_CLIENT_ID> \
  --role "AzureML Data Scientist" \
  --scope "/subscriptions/6ab08646-8f78-4187-ac87-c762aa843c9b/resourceGroups/mlmodel/providers/Microsoft.MachineLearningServices/workspaces/samplemodel"

# Assign Container Registry permissions
az role assignment create \
  --assignee <APPLICATION_CLIENT_ID> \
  --role "AcrPush" \
  --scope "/subscriptions/6ab08646-8f78-4187-ac87-c762aa843c9b/resourceGroups/mlmodel/providers/Microsoft.ContainerRegistry/registries/aksinstant"
```

### Step 3A: Setup OIDC (Workload Identity Federation) - **RECOMMENDED**

#### In Azure Portal:
1. **Go to your App Registration** → Certificates & secrets → Federated credentials
2. **Click "Add credential"**
3. **Configure for GitHub Actions:**
   - Federated credential scenario: "GitHub Actions deploying Azure resources"
   - Organization: `<your-github-username>`
   - Repository: `<your-repo-name>`
   - Entity type: "Environment"
   - GitHub environment name: `development`
   - Name: `github-actions-dev`

4. **Repeat for other environments:**
   - Create separate federated credentials for `staging` and `production` environments

#### In GitHub Repository:
1. **Go to Settings** → Secrets and variables → Actions
2. **Add Repository Secrets:**
   ```
   AZURE_CLIENT_ID: <Application Client ID from Step 1>
   AZURE_TENANT_ID: <Directory Tenant ID from Step 1>
   ```

### Step 3B: Setup Service Principal with Secrets (Fallback)

#### In Azure Portal:
1. **Go to your App Registration** → Certificates & secrets
2. **Click "New client secret"**
   - Description: `github-actions-secret`
   - Expires: 24 months (set calendar reminder to rotate)
3. **Copy the secret value** (you won't see it again!)

#### In GitHub Repository:
1. **Go to Settings** → Secrets and variables → Actions
2. **Add Repository Secrets:**
   ```
   AZURE_CLIENT_ID: <Application Client ID>
   AZURE_CLIENT_SECRET: <Client Secret Value>
   AZURE_TENANT_ID: <Directory Tenant ID>
   ```

### Step 4: Configure GitHub Environments

1. **Go to Settings** → Environments
2. **Create environments:**
   - `development` - No protection rules
   - `staging` - Required reviewers: 1 person
   - `production` - Required reviewers: 2+ people, deployment branches: `main` only

### Step 5: Test the Setup

1. **Run the workflow manually:**
   ```bash
   # Go to Actions tab in GitHub
   # Select "Deploy ML Health Check to Azure ML Studio"
   # Click "Run workflow" 
   # Select environment: dev
   ```

2. **Check the logs for:**
   ```
   ✅ Successfully authenticated to Azure
   ✅ Successfully connected to ML workspace
   ✅ Deployment completed successfully
   ```

## 🔧 Local Development Setup

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Set default subscription
az account set --subscription "6ab08646-8f78-4187-ac87-c762aa843c9b"

# Test ML workspace access
az ml workspace show --name samplemodel --resource-group mlmodel

# Run deployment locally
python deploy_to_azure_ml.py
```

## 🐛 Troubleshooting

### Common Issues:

#### 1. "DefaultAzureCredential failed to retrieve a token"
**Solution:** 
- Verify GitHub secrets are correctly set
- Check that the service principal has proper permissions
- Ensure federated credentials are configured for the right GitHub repo/environment

#### 2. "Insufficient privileges to complete the operation"
**Solution:**
```bash
# Grant additional permissions
az role assignment create \
  --assignee <APPLICATION_CLIENT_ID> \
  --role "Contributor" \
  --scope "/subscriptions/6ab08646-8f78-4187-ac87-c762aa843c9b/resourceGroups/mlmodel"
```

#### 3. "Unable to connect to Azure Container Registry"
**Solution:**
```bash
# Grant ACR permissions
az role assignment create \
  --assignee <APPLICATION_CLIENT_ID> \
  --role "AcrPush" \
  --scope "/subscriptions/6ab08646-8f78-4187-ac87-c762aa843c9b/resourceGroups/mlmodel/providers/Microsoft.ContainerRegistry/registries/aksinstant"
```

#### 4. Local Development Issues
```bash
# Re-authenticate
az logout
az login

# Check current account
az account show

# List available subscriptions
az account list --output table
```

## 🔒 Security Best Practices

### ✅ DO:
- Use OIDC/Workload Identity Federation when possible
- Rotate service principal secrets every 6-12 months
- Use least-privilege permissions
- Use separate service principals per environment
- Monitor authentication logs

### ❌ DON'T:
- Store secrets in code or commit them to git
- Use overly broad permissions like "Owner"
- Share service principal credentials between projects
- Use the same credentials for all environments

## 📊 Monitoring & Alerting

Set up monitoring for:
- Authentication failures
- Deployment failures
- Resource costs
- Security alerts

```bash
# Create alert rule for failed authentications
az monitor metrics alert create \
  --name "ML-Pipeline-Auth-Failures" \
  --resource-group mlmodel \
  --condition "avg SigninLogs_CL | where ResultType != 0" \
  --description "Alert when authentication failures occur"
```

## 🔄 Regular Maintenance

### Monthly:
- Review access logs
- Check for unused resources
- Update dependencies

### Quarterly:
- Review and rotate secrets
- Update permissions
- Test disaster recovery

### Annually:
- Full security audit
- Review compliance requirements
- Update documentation

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Azure Activity Logs
3. Check GitHub Actions logs
4. Verify all permissions are correctly set

## 🔗 References

- [Azure Workload Identity Federation](https://docs.microsoft.com/en-us/azure/active-directory/develop/workload-identity-federation)
- [GitHub Actions Azure Login](https://github.com/Azure/login)
- [Azure ML CLI Reference](https://docs.microsoft.com/en-us/cli/azure/ml)
- [Azure RBAC Best Practices](https://docs.microsoft.com/en-us/azure/role-based-access-control/best-practices) 