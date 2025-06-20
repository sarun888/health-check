#!/usr/bin/env python3
"""
Azure ML Deployment Script
Deploys ML model to Azure ML managed online endpoint
"""

import os
import logging
from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    ManagedOnlineEndpoint,
    ManagedOnlineDeployment,
    Model,
    CodeConfiguration,
    Environment
)
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main deployment function"""
    try:
        # Get configuration from environment variables
        subscription_id = os.environ.get("SUBSCRIPTION_ID")
        resource_group = os.environ.get("RESOURCE_GROUP")
        workspace_name = os.environ.get("WORKSPACE_NAME")
        image_uri = os.environ.get("IMAGE_URI")
        
        if not all([subscription_id, resource_group, workspace_name, image_uri]):
            raise ValueError("Missing required environment variables")
        
        logger.info(f"Deploying to Azure ML workspace: {workspace_name}")
        
        # Initialize ML Client
        credential = DefaultAzureCredential()
        ml_client = MLClient(
            credential=credential,
            subscription_id=subscription_id,
            resource_group_name=resource_group,
            workspace_name=workspace_name
        )
        
        # Define endpoint name
        endpoint_name = "ml-model-endpoint"
        deployment_name = "ml-model-deployment"
        
        # Create managed online endpoint
        endpoint = ManagedOnlineEndpoint(
            name=endpoint_name,
            description="ML Model API Endpoint",
            auth_mode="key",
            tags={
                "project": "ml-model-api",
                "environment": "production",
                "version": "1.0.0"
            }
        )
        
        try:
            logger.info(f"Creating endpoint: {endpoint_name}")
            ml_client.online_endpoints.begin_create_or_update(endpoint).result()
            logger.info(f"Endpoint {endpoint_name} created successfully")
        except ResourceExistsError:
            logger.info(f"Endpoint {endpoint_name} already exists")
        
        # Create environment from container image
        environment = Environment(
            name="ml-model-env",
            version="1.0.0",
            description="ML Model Environment",
            image=image_uri,
            inference_config={
                "liveness_route": {
                    "path": "/health",
                    "port": 8080
                },
                "readiness_route": {
                    "path": "/readiness",
                    "port": 8080
                },
                "scoring_route": {
                    "path": "/predict",
                    "port": 8080
                }
            }
        )
        
        # Create deployment
        deployment = ManagedOnlineDeployment(
            name=deployment_name,
            endpoint_name=endpoint_name,
            environment=environment,
            instance_type="Standard_DS2_v2",
            instance_count=1,
            request_settings={
                "request_timeout_ms": 30000,
                "max_concurrent_requests_per_instance": 1,
                "max_queue_wait_ms": 30000
            },
            liveness_probe={
                "failure_threshold": 3,
                "success_threshold": 1,
                "timeout": 30,
                "period": 30,
                "initial_delay": 60
            },
            readiness_probe={
                "failure_threshold": 3,
                "success_threshold": 1,
                "timeout": 30,
                "period": 30,
                "initial_delay": 60
            },
            environment_variables={
                "FLASK_ENV": "production",
                "PORT": "8080"
            },
            tags={
                "project": "ml-model-api",
                "environment": "production",
                "deployment_type": "online"
            }
        )
        
        logger.info(f"Creating deployment: {deployment_name}")
        ml_client.online_deployments.begin_create_or_update(deployment).result()
        logger.info(f"Deployment {deployment_name} created successfully")
        
        # Allocate traffic to the deployment
        logger.info("Allocating traffic to deployment")
        endpoint.traffic = {deployment_name: 100}
        ml_client.online_endpoints.begin_create_or_update(endpoint).result()
        
        # Get endpoint details
        endpoint_details = ml_client.online_endpoints.get(endpoint_name)
        logger.info(f"Endpoint URI: {endpoint_details.scoring_uri}")
        logger.info(f"Endpoint Key: {ml_client.online_endpoints.get_keys(endpoint_name).primary_key}")
        
        # Test the deployment
        test_deployment(ml_client, endpoint_name)
        
        logger.info("Deployment completed successfully!")
        
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise

def test_deployment(ml_client, endpoint_name):
    """Test the deployed endpoint"""
    try:
        logger.info("Testing deployment...")
        
        # Sample test data
        test_data = {
            "features": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
                        0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        }
        
        # Make prediction request
        response = ml_client.online_endpoints.invoke(
            endpoint_name=endpoint_name,
            request_file=None,
            deployment_name=None,
            request_json=test_data
        )
        
        logger.info(f"Test prediction response: {response}")
        
    except Exception as e:
        logger.warning(f"Test failed: {str(e)}")

if __name__ == "__main__":
    main() 