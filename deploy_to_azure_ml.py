#!/usr/bin/env python3
"""
Azure ML Deployment Script
Deploys the ML Health Check application to Azure ML Studio as a managed endpoint
"""

import os
import sys
import json
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
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'registry_login_server': os.getenv('REGISTRY_LOGIN_SERVER', 'aksinstant.azurecr.io')
    }
    
    # Validate required configuration
    missing_vars = [k for k, v in config.items() if not v]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
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
        
        return client
        
    except Exception as e:
        print(f"❌ Failed to create ML client: {str(e)}")
        sys.exit(1)

def create_or_update_endpoint(client, config):
    """Create or update the managed online endpoint"""
    endpoint_name = f"ml-health-check-{config['environment']}"
    
    try:
        # Check if endpoint exists
        try:
            endpoint = client.online_endpoints.get(endpoint_name)
            print(f"✅ Endpoint {endpoint_name} already exists")
        except ResourceNotFoundError:
            print(f"📝 Creating new endpoint: {endpoint_name}")
            
            # Create endpoint
            endpoint = ManagedOnlineEndpoint(
                name=endpoint_name,
                description=f"ML Health Check endpoint for {config['environment']} environment",
                auth_mode="key",
                tags={
                    "environment": config['environment'],
                    "project": "ml-health-check",
                    "managed_by": "github-actions"
                }
            )
            
            client.online_endpoints.begin_create_or_update(endpoint).result()
            print(f"✅ Endpoint {endpoint_name} created successfully")
        
        return endpoint_name
        
    except Exception as e:
        print(f"❌ Failed to create/update endpoint: {str(e)}")
        sys.exit(1)

def create_or_update_deployment(client, endpoint_name, config):
    """Create or update the deployment"""
    deployment_name = f"ml-deploy-{config['environment']}"
    
    try:
        print(f"🚀 Creating/updating deployment: {deployment_name}")
        
        # Create environment from container image
        environment = Environment(
            name=f"ml-env-{config['environment']}",
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
                initial_delay=10,
                path="/health"
            ),
            readiness_probe=ProbeSettings(
                failure_threshold=10,
                success_threshold=1,
                timeout=10,
                period=10,
                initial_delay=10,
                path="/health"
            )
        )
        
        # Deploy
        client.online_deployments.begin_create_or_update(deployment).result()
        print(f"✅ Deployment {deployment_name} completed successfully")
        
        # Set traffic to 100% for this deployment
        endpoint = client.online_endpoints.get(endpoint_name)
        endpoint.traffic = {deployment_name: 100}
        client.online_endpoints.begin_create_or_update(endpoint).result()
        print(f"✅ Traffic routed to deployment: {deployment_name}")
        
        return deployment_name
        
    except Exception as e:
        print(f"❌ Failed to create/update deployment: {str(e)}")
        sys.exit(1)

def get_endpoint_details(client, endpoint_name, config):
    """Get endpoint details and set output for GitHub Actions"""
    try:
        endpoint = client.online_endpoints.get(endpoint_name)
        endpoint_uri = endpoint.scoring_uri
        
        print(f"🌐 Endpoint Details:")
        print(f"   Name: {endpoint_name}")
        print(f"   URI: {endpoint_uri}")
        print(f"   Status: {endpoint.provisioning_state}")
        
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

def test_endpoint(endpoint_uri):
    """Test the deployed endpoint"""
    if not endpoint_uri:
        print("⚠️  No endpoint URI available for testing")
        return
    
    try:
        import requests
        import time
        
        print(f"🧪 Testing endpoint: {endpoint_uri}")
        
        # Wait for endpoint to be ready
        print("⏳ Waiting for endpoint to be ready...")
        time.sleep(30)
        
        # Test health endpoint
        health_url = endpoint_uri.replace('/score', '/health') if '/score' in endpoint_uri else f"{endpoint_uri}/health"
        
        response = requests.get(health_url, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.status_code}")
            print(f"   Response: {response.text}")
        else:
            print(f"⚠️  Health check returned: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"⚠️  Endpoint test failed: {str(e)}")
        print("   This is normal for new deployments - the endpoint may still be starting up")

def main():
    """Main deployment function"""
    print("🚀 Starting Azure ML Deployment")
    print("=" * 50)
    
    # Get configuration
    config = get_config()
    
    print(f"📋 Deployment Configuration:")
    print(f"   Environment: {config['environment']}")
    print(f"   Workspace: {config['workspace_name']}")
    print(f"   Resource Group: {config['resource_group']}")
    print(f"   Image: {config['image_uri']}")
    print("")
    
    # Create ML client
    client = create_ml_client(config)
    
    # Create or update endpoint
    endpoint_name = create_or_update_endpoint(client, config)
    
    # Create or update deployment
    deployment_name = create_or_update_deployment(client, endpoint_name, config)
    
    # Get endpoint details
    endpoint_uri = get_endpoint_details(client, endpoint_name, config)
    
    # Test the endpoint
    test_endpoint(endpoint_uri)
    
    print("=" * 50)
    print(f"🎉 Deployment completed successfully!")
    print(f"   Endpoint: {endpoint_name}")
    print(f"   URI: {endpoint_uri}")
    print(f"   Environment: {config['environment']}")

if __name__ == "__main__":
    main() 