#!/usr/bin/env python3
"""
Script to update GitHub Actions workflow from OIDC to Client Secret authentication
"""

def fix_workflow():
    workflow_file = '.github/workflows/deploy-to-azure-ml.yml'
    
    # Read the file
    with open(workflow_file, 'r') as f:
        content = f.read()
    
    # Replace OIDC authentication with Client Secret authentication
    old_auth = """      # Azure authentication using OIDC (Workload Identity Federation)
      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ env.SUBSCRIPTION_ID }}"""
    
    new_auth = """      # Azure authentication using Client Secret
      - name: Azure Login (Client Secret)
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}"""
    
    # Replace for cleanup job
    old_cleanup_auth = """      # Azure authentication for cleanup operations
      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ env.SUBSCRIPTION_ID }}"""
    
    new_cleanup_auth = """      # Azure authentication for cleanup operations
      - name: Azure Login (Client Secret)
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}"""
    
    # Perform replacements
    content = content.replace(old_auth, new_auth)
    content = content.replace(old_cleanup_auth, new_cleanup_auth)
    
    # Write back to file
    with open(workflow_file, 'w') as f:
        f.write(content)
    
    print("✅ Workflow updated successfully!")
    print("🔐 Now add the AZURE_CREDENTIALS secret to GitHub:")
    print("""
{
  "clientId": "YOUR_AZURE_CLIENT_ID_VALUE",
  "clientSecret": "YOUR_AZURE_CLIENT_SECRET_VALUE", 
  "subscriptionId": "6ab08646-8f78-4187-ac87-c762aa843c9b",
  "tenantId": "YOUR_AZURE_TENANT_ID_VALUE"
}
""")

if __name__ == "__main__":
    fix_workflow() 