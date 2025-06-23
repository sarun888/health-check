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
    Environment,
    OnlineRequestSettings,
    ProbeSettings
)
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError

def get_config():
    config = {
        'subscription_id': os.getenv('SUBSCRIPTION_ID' ,'6ab08646-8f78-4187-ac87-c762aa843c9b'),
        'resource_group': os.getenv('RESOURCE_GROUP' ,'mlmodel'),
        'workspace_name': os.getenv('WORKSPACE_NAME' ,'samplemodel'),
        'image_uri': os.getenv('IMAGE_URI' ,'aksinstant.azurecr.io/ml-health-check:latest'),
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'registry_login_server': os.getenv('REGISTRY_LOGIN_SERVER')
    }
    missing_vars = [k for k, v in config.items() if not v]
    if missing_vars:
        print(f"❌ Missing required env vars: {', '.join(missing_vars)}")
        sys.exit(1)
    return config

def create_ml_client(config):
    try:
        print("🔐 Authenticating to Azure ML...")
        credential = DefaultAzureCredential()
        client = MLClient(
            credential,
            subscription_id=config['subscription_id'],
            resource_group_name=config['resource_group'],
            workspace_name=config['workspace_name']
        )
        print(f"✅ Connected to workspace: {client.workspaces.get(config['workspace_name']).name}")
        return client
    except Exception as e:
        print(f"❌ Auth failure: {str(e)}")
        sys.exit(1)

def create_or_update_endpoint(client, config):
    endpoint_name = f"ml-health-check-{config['environment']}"
    try:
        try:
            _ = client.online_endpoints.get(endpoint_name)
            print(f"✅ Endpoint exists: {endpoint_name}")
        except ResourceNotFoundError:
            print(f"📝 Creating endpoint: {endpoint_name}")
            endpoint = ManagedOnlineEndpoint(
                name=endpoint_name,
                description=f"ML Health Check for {config['environment']}",
                auth_mode="key",
                tags={
                    "env": config['environment'],
                    "project": "ml-health-check",
                    "managed_by": "github-actions"
                }
            )
            client.online_endpoints.begin_create_or_update(endpoint).result()
            print(f"✅ Created endpoint: {endpoint_name}")
        return endpoint_name
    except Exception as e:
        print(f"❌ Endpoint error: {str(e)}")
        sys.exit(1)

def create_or_update_deployment(client, endpoint_name, config):
    deployment_name = f"ml-deploy-{config['environment']}"
    try:
        print(f"🚀 Deploying: {deployment_name}")
        env = Environment(
            name=f"ml-env-{config['environment']}",
            image=config['image_uri'],
            description=f"Env from image {config['image_uri']}"
        )
        deployment = ManagedOnlineDeployment(
            name=deployment_name,
            endpoint_name=endpoint_name,
            environment=env,
            instance_type="Standard_DS3_v2",
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
        client.online_deployments.begin_create_or_update(deployment).result()
        print(f"✅ Deployment complete: {deployment_name}")

        endpoint = client.online_endpoints.get(endpoint_name)
        endpoint.traffic = {deployment_name: 100}
        client.online_endpoints.begin_create_or_update(endpoint).result()
        print(f"✅ Traffic routed to: {deployment_name}")
        return deployment_name
    except Exception as e:
        print(f"❌ Deployment error: {str(e)}")
        sys.exit(1)

def get_endpoint_details(client, endpoint_name):
    try:
        endpoint = client.online_endpoints.get(endpoint_name)
        uri = endpoint.scoring_uri
        print("🌐 Endpoint details:")
        print(f"   Name: {endpoint_name}")
        print(f"   URI: {uri}")
        print(f"   Status: {endpoint.provisioning_state}")

        github_output = os.getenv("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"endpoint-uri={uri}\n")
                f.write(f"endpoint-name={endpoint_name}\n")
        os.environ["ENDPOINT_URI"] = uri
        return uri
    except Exception as e:
        print(f"❌ Failed to get endpoint: {str(e)}")
        return None

def test_endpoint(uri):
    if not uri:
        print("⚠️  No URI found for testing")
        return
    try:
        import requests
        import time

        print(f"⏳ Waiting 30s for endpoint to stabilize...")
        time.sleep(30)

        # Test health
        health_resp = requests.get(f"{uri}/health", timeout=30)
        print(f"✅ Health: {health_resp.status_code}")
        print(health_resp.text)

        # Optional: Test scoring (POST)
        try:
            score_payload = {"inputs": [[5.1, 3.5, 1.4, 0.2]]}  # example for iris
            score_resp = requests.post(f"{uri}/score", json=score_payload, timeout=30)
            print(f"✅ Score status: {score_resp.status_code}")
            print(f"Response: {score_resp.text}")
        except Exception as e:
            print(f"⚠️  /score test failed: {str(e)}")

    except Exception as e:
        print(f"⚠️  Endpoint unreachable: {str(e)}")

def main():
    print("🚀 Starting Azure ML Deployment")
    print("=" * 50)

    config = get_config()
    client = create_ml_client(config)
    endpoint_name = create_or_update_endpoint(client, config)
    _ = create_or_update_deployment(client, endpoint_name, config)
    uri = get_endpoint_details(client, endpoint_name)
    test_endpoint(uri)

    print("=" * 50)
    print(f"🎉 Deployment complete!")
    print(f"Endpoint URI: {uri}")
    print(f"Environment: {config['environment']}")

if __name__ == "__main__":
    main()
