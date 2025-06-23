#!/usr/bin/env python3
"""
Production Azure ML Deployment Script
Properly deploys the ML Health Check application to Azure ML Studio as a managed endpoint
"""

import os
import sys
import json
import time
from pathlib import Path
from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    ManagedOnlineEndpoint,
    ManagedOnlineDeployment,
    Model,
    Environment,
    CodeConfiguration,
    OnlineRequestSettings,
    ProbeSettings
)
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError

def get_config():
    """Get configuration from environment variables"""
    config = {
        'subscription_id': os.getenv('SUBSCRIPTION_ID'),
        'resource_group': os.getenv('RESOURCE_GROUP'),
        'workspace_name': os.getenv('WORKSPACE_NAME'),
        'image_uri': os.getenv('IMAGE_URI'),
        'environment': os.getenv('ENVIRONMENT', 'staging'),
        'registry_login_server': os.getenv('REGISTRY_LOGIN_SERVER', 'aksinstant.azurecr.io')
    }
    
    # Validate required configuration
    missing_vars = [k for k, v in config.items() if not v]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Required variables:")
        for var in missing_vars:
            print(f"   - {var}")
        sys.exit(1)
    
    print("✅ Configuration loaded:")
    for key, value in config.items():
        if key == 'image_uri':
            print(f"   {key}: {value[:50]}...")
        else:
            print(f"   {key}: {value}")
    
    return config

def create_ml_client(config):
    """Create Azure ML client with proper authentication"""
    try:
        print(f"🔐 Authenticating to Azure ML...")
        credential = DefaultAzureCredential()
        
        client = MLClient(
            credential=credential,
            subscription_id=config['subscription_id'],
            resource_group_name=config['resource_group'],
            workspace_name=config['workspace_name']
        )
        
        # Test the connection
        workspace = client.workspaces.get(config['workspace_name'])
        print(f"✅ Connected to ML workspace: {workspace.display_name}")
        print(f"   Location: {workspace.location}")
        print(f"   Resource Group: {workspace.resource_group}")
        
        return client
        
    except Exception as e:
        print(f"❌ Failed to create ML client: {str(e)}")
        print("Debug info:")
        print(f"   Subscription: {config['subscription_id']}")
        print(f"   Resource Group: {config['resource_group']}")
        print(f"   Workspace: {config['workspace_name']}")
        sys.exit(1)

def create_or_update_endpoint(client, config):
    """Create or update the managed online endpoint"""
    endpoint_name = f"ml-health-check-{config['environment']}"
    
    try:
        # Check if endpoint exists
        try:
            endpoint = client.online_endpoints.get(endpoint_name)
            print(f"✅ Endpoint {endpoint_name} already exists")
            print(f"   Status: {endpoint.provisioning_state}")
            print(f"   Auth Mode: {endpoint.auth_mode}")
        except ResourceNotFoundError:
            print(f"📝 Creating new endpoint: {endpoint_name}")
            
            # Create endpoint
            endpoint = ManagedOnlineEndpoint(
                name=endpoint_name,
                description=f"ML Health Check endpoint for {config['environment']} environment",
                auth_mode="key",
                public_network_access="enabled",
                tags={
                    "environment": config['environment'],
                    "project": "ml-health-check",
                    "managed_by": "github-actions",
                    "version": "1.0.0"
                }
            )
            
            print("⏳ Creating endpoint (this may take 2-5 minutes)...")
            poller = client.online_endpoints.begin_create_or_update(endpoint)
            result = poller.result()
            print(f"✅ Endpoint {endpoint_name} created successfully")
        
        return endpoint_name
        
    except Exception as e:
        print(f"❌ Failed to create/update endpoint: {str(e)}")
        print(f"Full error: {repr(e)}")
        sys.exit(1)

def create_or_update_deployment(client, endpoint_name, config):
    """Create or update the deployment"""
    deployment_name = f"ml-deploy-{config['environment']}"
    
    try:
        print(f"🚀 Creating/updating deployment: {deployment_name}")
        print(f"   Using image: {config['image_uri']}")
        
        # Create environment from container image
        environment = Environment(
            name=f"ml-environment-{config['environment']}",
            image=config['image_uri'],
            description=f"Container environment for ML Health Check - {config['environment']}",
        )
        
        # Create deployment with proper Azure ML SDK objects
        deployment = ManagedOnlineDeployment(
            name=deployment_name,
            endpoint_name=endpoint_name,
            environment=environment,
            instance_type="Standard_DS3_v2",  # Use recommended instance size
            instance_count=1,
            request_settings=OnlineRequestSettings(
                request_timeout_ms=90000,
                max_concurrent_requests_per_instance=1,
                max_queue_wait_ms=500
            ),
            liveness_probe=ProbeSettings(
                failure_threshold=3,
                success_threshold=1,
                timeout=2,
                period=10,
                initial_delay=30
            ),
            readiness_probe=ProbeSettings(
                failure_threshold=10,
                success_threshold=1,
                timeout=10,
                period=10,
                initial_delay=30
            )
        )
        
        print("⏳ Creating deployment (this may take 10-15 minutes)...")
        print("   You can monitor progress in Azure ML Studio")
        
        # Deploy with timeout and progress tracking
        poller = client.online_deployments.begin_create_or_update(deployment)
        
        # Wait for completion
        result = poller.result()
        print(f"✅ Deployment {deployment_name} completed successfully")
        
        # Wait a bit before setting traffic
        print("⏳ Waiting for deployment to stabilize...")
        time.sleep(30)
        
        # Set traffic to 100% for this deployment
        print("🚦 Setting traffic to 100% for new deployment...")
        endpoint = client.online_endpoints.get(endpoint_name)
        endpoint.traffic = {deployment_name: 100}
        client.online_endpoints.begin_create_or_update(endpoint).result()
        print(f"✅ Traffic routed to deployment: {deployment_name}")
        
        return deployment_name
        
    except Exception as e:
        print(f"❌ Failed to create/update deployment: {str(e)}")
        print(f"Full error: {repr(e)}")
        
        # Try to get more details about the failure
        try:
            deployments = client.online_deployments.list(endpoint_name)
            print("📋 Current deployments:")
            for dep in deployments:
                print(f"   - {dep.name}: {dep.provisioning_state}")
        except:
            pass
        
        sys.exit(1)

def get_endpoint_details(client, endpoint_name, config):
    """Get endpoint details and set output for GitHub Actions"""
    try:
        endpoint = client.online_endpoints.get(endpoint_name)
        endpoint_uri = endpoint.scoring_uri
        
        print(f"🌐 Deployment Complete! Endpoint Details:")
        print(f"   Name: {endpoint_name}")
        print(f"   Scoring URI: {endpoint_uri}")
        print(f"   Status: {endpoint.provisioning_state}")
        print(f"   Auth Mode: {endpoint.auth_mode}")
        
        # Get endpoint keys for authentication
        try:
            keys = client.online_endpoints.get_keys(endpoint_name)
            print(f"   🔑 Primary Key: {keys.primary_key[:20]}...")
        except:
            print("   ⚠️ Could not retrieve endpoint keys")
        
        # Set GitHub Actions output
        github_output = os.getenv('GITHUB_OUTPUT')
        if github_output:
            with open(github_output, 'a') as f:
                f.write(f"endpoint-uri={endpoint_uri}\n")
                f.write(f"endpoint-name={endpoint_name}\n")
        
        # Set environment variable for health check
        os.environ['ENDPOINT_URI'] = endpoint_uri
        
        return endpoint_uri
        
    except Exception as e:
        print(f"❌ Failed to get endpoint details: {str(e)}")
        return None

def test_endpoint(client, endpoint_name, endpoint_uri):
    """Test the deployed endpoint"""
    if not endpoint_uri:
        print("⚠️  No endpoint URI available for testing")
        return False
    
    try:
        import requests
        
        print(f"🧪 Testing endpoint: {endpoint_uri}")
        
        # Get authentication key
        keys = client.online_endpoints.get_keys(endpoint_name)
        headers = {
            'Authorization': f'Bearer {keys.primary_key}',
            'Content-Type': 'application/json'
        }
        
        # Test health endpoint
        print("1. Testing health endpoint...")
        health_response = requests.get(
            endpoint_uri.replace('/score', '/health'),
            headers=headers,
            timeout=30
        )
        
        if health_response.status_code == 200:
            print("   ✅ Health check passed")
        else:
            print(f"   ⚠️ Health check returned: {health_response.status_code}")
        
        # Test scoring endpoint
        print("2. Testing scoring endpoint...")
        test_data = {
            "data": [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
                     11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]]
        }
        
        response = requests.post(
            endpoint_uri,
            json=test_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ Scoring test passed")
            print(f"   📊 Prediction result: {result}")
            return True
        else:
            print(f"   ❌ Scoring test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Endpoint testing failed: {str(e)}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Starting Azure ML Production Deployment")
    print("=" * 50)
    
    try:
        # Get configuration
        config = get_config()
        
        # Create ML client
        client = create_ml_client(config)
        
        # Create or update endpoint
        endpoint_name = create_or_update_endpoint(client, config)
        
        # Create or update deployment
        deployment_name = create_or_update_deployment(client, endpoint_name, config)
        
        # Get endpoint details
        endpoint_uri = get_endpoint_details(client, endpoint_name, config)
        
        # Test the endpoint
        test_success = test_endpoint(client, endpoint_name, endpoint_uri)
        
        print("\n" + "=" * 50)
        if test_success:
            print("🎉 DEPLOYMENT SUCCESSFUL!")
            print(f"   Your model is deployed and ready at: {endpoint_uri}")
            print("\n📋 Next Steps:")
            print("   1. Test your endpoint using the scoring URI")
            print("   2. Monitor performance in Azure ML Studio")
            print("   3. Set up monitoring and alerts")
        else:
            print("⚠️  DEPLOYMENT COMPLETED WITH WARNINGS")
            print(f"   Endpoint is deployed but tests failed: {endpoint_uri}")
            print("   Please check Azure ML Studio for more details")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 