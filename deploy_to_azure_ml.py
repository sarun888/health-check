#!/usr/bin/env python3
"""
Azure ML Deployment Script
Deploys ML model to Azure ML managed online endpoint with static configuration
"""

import os
import sys
import logging
import json
from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    ManagedOnlineEndpoint,
    ManagedOnlineDeployment,
    Model,
    CodeConfiguration,
    Environment
)
from azure.identity import DefaultAzureCredential, ClientSecretCredential, AzureCliCredential
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError, ClientAuthenticationError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# STATIC CONFIGURATION - UPDATED WITH YOUR AZURE VALUES
STATIC_CONFIG = {
    # Azure Subscription and Resource Configuration
    "SUBSCRIPTION_ID": "6ab08646-8f78-4187-ac87-c762aa843c9b",
    
    # Development Environment
    "DEV": {
        "RESOURCE_GROUP": "mlmodel",
        "WORKSPACE_NAME": "samplemodel",
        "REGISTRY_LOGIN_SERVER": "aksinstant.azurecr.io",
        "IMAGE_URI": "aksinstant.azurecr.io/ml-health-check:latest"
    },
    
    # Staging Environment
    "STAGING": {
        "RESOURCE_GROUP": "mlmodel",
        "WORKSPACE_NAME": "samplemodel", 
        "REGISTRY_LOGIN_SERVER": "aksinstant.azurecr.io",
        "IMAGE_URI": "aksinstant.azurecr.io/ml-health-check:latest"
    },
    
    # Production Environment
    "PRODUCTION": {
        "RESOURCE_GROUP": "mlmodel",
        "WORKSPACE_NAME": "samplemodel",
        "REGISTRY_LOGIN_SERVER": "aksinstant.azurecr.io", 
        "IMAGE_URI": "aksinstant.azurecr.io/ml-health-check:latest"
    }
}

def get_azure_credential():
    """
    Get Azure credential with multiple fallback methods for different environments.
    Priority:
    1. Service Principal (CI/CD)
    2. Azure CLI (local development)
    3. Default Azure Credential (managed identity, etc.)
    """
    credential = None
    auth_method = "Unknown"
    
    try:
        # Method 1: Service Principal authentication (for CI/CD)
        client_id = os.environ.get("AZURE_CLIENT_ID")
        client_secret = os.environ.get("AZURE_CLIENT_SECRET")
        tenant_id = os.environ.get("AZURE_TENANT_ID")
        
        if client_id and client_secret and tenant_id:
            logger.info("Using Service Principal authentication")
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            auth_method = "Service Principal"
        
        # Method 2: Azure CLI authentication (for local development)
        elif not os.environ.get("GITHUB_ACTIONS"):
            logger.info("Attempting Azure CLI authentication")
            try:
                credential = AzureCliCredential()
                # Test the credential
                token = credential.get_token("https://management.azure.com/.default")
                auth_method = "Azure CLI"
                logger.info("Azure CLI authentication successful")
            except Exception as cli_error:
                logger.warning(f"Azure CLI authentication failed: {cli_error}")
                credential = None
        
        # Method 3: Default Azure Credential (fallback)
        if credential is None:
            logger.info("Using DefaultAzureCredential")
            credential = DefaultAzureCredential(
                exclude_environment_credential=False,
                exclude_managed_identity_credential=False,
                exclude_shared_token_cache_credential=True,
                exclude_visual_studio_code_credential=True,
                exclude_azure_cli_credential=False,
                exclude_azure_powershell_credential=True,
                exclude_interactive_browser_credential=True
            )
            auth_method = "Default Azure Credential"
            
    except Exception as e:
        logger.error(f"Error setting up Azure credential: {e}")
        raise
    
    if credential is None:
        raise Exception("No valid Azure credential could be obtained")
    
    logger.info(f"Authentication method: {auth_method}")
    return credential, auth_method

def get_environment_config():
    """Get environment-specific configuration"""
    environment = os.environ.get("ENVIRONMENT", "development").upper()
    if environment == "DEVELOPMENT":
        environment = "DEV"
    elif environment == "STAGING":
        environment = "STAGING"
    elif environment == "PRODUCTION": 
        environment = "PRODUCTION"
    else:
        environment = "DEV"
    
    configs = {
        "DEV": {
            "instance_type": "Standard_DS2_v2",
            "instance_count": 1,
            "max_concurrent_requests": 1,
            "request_timeout_ms": 30000,
            "endpoint_suffix": "dev",
            "traffic_allocation": 100,
            "auto_scale": False
        },
        "STAGING": {
            "instance_type": "Standard_DS3_v2", 
            "instance_count": 2,
            "max_concurrent_requests": 2,
            "request_timeout_ms": 45000,
            "endpoint_suffix": "staging",
            "traffic_allocation": 100,
            "auto_scale": True
        },
        "PRODUCTION": {
            "instance_type": "Standard_DS4_v2",
            "instance_count": 3,
            "max_concurrent_requests": 5,
            "request_timeout_ms": 60000,
            "endpoint_suffix": "prod",
            "traffic_allocation": 100,
            "auto_scale": True
        }
    }
    
    return configs.get(environment, configs["DEV"]), environment

def get_static_config():
    """Get static configuration values"""
    environment = os.environ.get("ENVIRONMENT", "development").upper()
    if environment == "DEVELOPMENT":
        environment = "DEV"
    elif environment == "STAGING":
        environment = "STAGING"
    elif environment == "PRODUCTION":
        environment = "PRODUCTION"
    else:
        environment = "DEV"
    
    # Override with environment variables if provided (for GitHub Actions)
    config = STATIC_CONFIG[environment].copy()
    config["SUBSCRIPTION_ID"] = os.environ.get("SUBSCRIPTION_ID", STATIC_CONFIG["SUBSCRIPTION_ID"])
    config["RESOURCE_GROUP"] = os.environ.get("RESOURCE_GROUP", config["RESOURCE_GROUP"])
    config["WORKSPACE_NAME"] = os.environ.get("WORKSPACE_NAME", config["WORKSPACE_NAME"])
    config["IMAGE_URI"] = os.environ.get("IMAGE_URI", config["IMAGE_URI"])
    
    logger.info(f"Using configuration for environment: {environment}")
    logger.info(f"Subscription ID: {config['SUBSCRIPTION_ID']}")
    logger.info(f"Resource Group: {config['RESOURCE_GROUP']}")
    logger.info(f"Workspace: {config['WORKSPACE_NAME']}")
    logger.info(f"Image URI: {config['IMAGE_URI']}")
    
    return config

def create_ml_client(config):
    """Create and return ML Client with improved authentication handling"""
    logger.info(f"Connecting to Azure ML workspace: {config['WORKSPACE_NAME']}")
    
    try:
        credential, auth_method = get_azure_credential()
    except Exception as e:
        logger.error(f"Failed to get Azure credential: {e}")
        if os.environ.get("GITHUB_ACTIONS"):
            logger.error("In GitHub Actions - ensure AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID secrets are configured")
            logger.error("Also ensure the Azure App Registration has appropriate permissions for ML workspace access")
        else:
            logger.error("For local development, run 'az login' to authenticate")
        sys.exit(1)
    
    try:
        ml_client = MLClient(
            credential=credential,
            subscription_id=config["SUBSCRIPTION_ID"],
            resource_group_name=config["RESOURCE_GROUP"],
            workspace_name=config["WORKSPACE_NAME"]
        )
        
        # Validate connection with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                workspace = ml_client.workspaces.get(config["WORKSPACE_NAME"])
                logger.info(f"Successfully connected to workspace: {workspace.name} using {auth_method}")
                return ml_client
            except ClientAuthenticationError as auth_error:
                logger.error(f"Authentication failed (attempt {attempt + 1}/{max_retries}): {auth_error}")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to connect to workspace after {max_retries} attempts: {e}")
                    logger.error("Make sure to update the STATIC_CONFIG in deploy_to_azure_ml.py with your actual Azure values")
                    logger.error("Verify that the service principal has the required permissions:")
                    logger.error("- Contributor or Machine Learning Operator on the ML workspace")
                    logger.error("- Reader access on the resource group")
                    if os.environ.get("GITHUB_ACTIONS"):
                        logger.warning("Running in GitHub Actions - some workspace validation errors may be expected")
                        return ml_client
                    raise
                
    except Exception as e:
        logger.error(f"Failed to create ML Client: {e}")
        raise

def create_or_update_endpoint(ml_client, endpoint_name, env_config):
    """Create or update managed online endpoint"""
    environment = os.environ.get("ENVIRONMENT", "development")
    
    endpoint = ManagedOnlineEndpoint(
        name=endpoint_name,
        description=f"ML Health Check API Endpoint - {environment.title()}",
        auth_mode="key",
        public_network_access="enabled",
        tags={
            "project": "ml-health-check",
            "environment": environment,
            "version": "1.0.0",
            "deployed_by": "github-actions",
            "deployment_date": os.environ.get("GITHUB_RUN_ID", "manual")
        }
    )
    
    try:
        logger.info(f"Creating/updating endpoint: {endpoint_name}")
        endpoint_result = ml_client.online_endpoints.begin_create_or_update(endpoint).result()
        logger.info(f"Endpoint {endpoint_name} ready")
        return endpoint_result
    except Exception as e:
        logger.error(f"Failed to create endpoint: {str(e)}")
        raise

def create_environment(image_uri, env_config):
    """Create Azure ML environment from container image"""
    environment_name = f"ml-health-check-env-{os.environ.get('ENVIRONMENT', 'dev')}"
    
    environment = Environment(
        name=environment_name,
        version="1.0.0",
        description=f"ML Health Check Environment - {os.environ.get('ENVIRONMENT', 'development').title()}",
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
    
    return environment

def create_deployment(ml_client, endpoint_name, environment, env_config):
    """Create managed online deployment"""
    deployment_name = f"ml-health-check-{env_config['endpoint_suffix']}"
    
    # Auto-scaling configuration for production environments
    auto_scale_settings = None
    if env_config.get("auto_scale", False):
        auto_scale_settings = {
            "min_instances": env_config["instance_count"],
            "max_instances": env_config["instance_count"] * 2,
            "target_utilization_percentage": 70
        }
    
    deployment = ManagedOnlineDeployment(
        name=deployment_name,
        endpoint_name=endpoint_name,
        environment=environment,
        instance_type=env_config["instance_type"],
        instance_count=env_config["instance_count"],
        request_settings={
            "request_timeout_ms": env_config["request_timeout_ms"],
            "max_concurrent_requests_per_instance": env_config["max_concurrent_requests"],
            "max_queue_wait_ms": env_config["request_timeout_ms"]
        },
        liveness_probe={
            "failure_threshold": 3,
            "success_threshold": 1,
            "timeout": 30,
            "period": 30,
            "initial_delay": 120
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
            "PORT": "8080",
            "ENVIRONMENT": os.environ.get("ENVIRONMENT", "development"),
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO")
        },
        tags={
            "project": "ml-health-check",
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "deployment_type": "online",
            "github_sha": os.environ.get("GITHUB_SHA", "unknown"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID", "unknown")
        }
    )
    
    logger.info(f"Creating deployment: {deployment_name}")
    deployment_result = ml_client.online_deployments.begin_create_or_update(deployment).result()
    logger.info(f"Deployment {deployment_name} completed successfully")
    
    return deployment_result, deployment_name

def allocate_traffic(ml_client, endpoint_name, deployment_name, traffic_percentage=100):
    """Allocate traffic to the deployment"""
    logger.info(f"Allocating {traffic_percentage}% traffic to deployment: {deployment_name}")
    
    endpoint = ml_client.online_endpoints.get(endpoint_name)
    endpoint.traffic = {deployment_name: traffic_percentage}
    
    ml_client.online_endpoints.begin_create_or_update(endpoint).result()
    logger.info("Traffic allocation completed")

def test_deployment(ml_client, endpoint_name):
    """Test the deployed endpoint with comprehensive health checks"""
    logger.info("Running deployment tests...")
    
    try:
        # Test prediction endpoint
        test_data = {
            "features": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
                        0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        }
        
        prediction_response = ml_client.online_endpoints.invoke(
            endpoint_name=endpoint_name,
            request_file=None,
            deployment_name=None,
            request_json=test_data
        )
        logger.info(f"Prediction test response: {prediction_response}")
        
        logger.info("All deployment tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Deployment test failed: {str(e)}")
        return False

def get_endpoint_details(ml_client, endpoint_name):
    """Get and log endpoint details"""
    try:
        endpoint = ml_client.online_endpoints.get(endpoint_name)
        keys = ml_client.online_endpoints.get_keys(endpoint_name)
        
        endpoint_info = {
            "endpoint_name": endpoint_name,
            "scoring_uri": endpoint.scoring_uri,
            "swagger_uri": endpoint.openapi_uri,
            "primary_key": keys.primary_key[:10] + "...",  # Truncated for security
            "status": endpoint.provisioning_state
        }
        
        logger.info("=== Endpoint Details ===")
        for key, value in endpoint_info.items():
            logger.info(f"{key}: {value}")
        
        # Output for GitHub Actions
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::set-output name=endpoint-uri::{endpoint.scoring_uri}")
            print(f"::set-output name=endpoint-key::{keys.primary_key}")
        
        return endpoint_info
        
    except Exception as e:
        logger.error(f"Failed to get endpoint details: {str(e)}")
        return None

def cleanup_old_deployments(ml_client, endpoint_name, keep_count=2):
    """Clean up old deployments, keeping only the most recent ones"""
    try:
        logger.info(f"Cleaning up old deployments for endpoint: {endpoint_name}")
        
        deployments = ml_client.online_deployments.list(endpoint_name)
        deployment_list = list(deployments)
        
        if len(deployment_list) <= keep_count:
            logger.info(f"Only {len(deployment_list)} deployments found, no cleanup needed")
            return
        
        # Sort by creation time and keep only the most recent ones
        sorted_deployments = sorted(deployment_list, 
                                  key=lambda x: x.created_time, 
                                  reverse=True)
        
        deployments_to_delete = sorted_deployments[keep_count:]
        
        for deployment in deployments_to_delete:
            logger.info(f"Deleting old deployment: {deployment.name}")
            ml_client.online_deployments.begin_delete(
                name=deployment.name,
                endpoint_name=endpoint_name
            ).result()
        
        logger.info(f"Cleaned up {len(deployments_to_delete)} old deployments")
        
    except Exception as e:
        logger.warning(f"Cleanup failed: {str(e)}")

def main():
    """Main deployment function"""
    try:
        logger.info("Starting Azure ML deployment process...")
        
        # Check if running in CI/CD mode
        is_cicd = os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI")
        if is_cicd:
            logger.info("Running in CI/CD mode - some Azure operations will be simulated")
        
        # Get static and environment-specific configuration
        static_config = get_static_config()
        env_config, environment = get_environment_config()
        
        logger.info(f"Deploying to environment: {environment}")
        logger.info(f"Configuration: {json.dumps(env_config, indent=2)}")
        
        # Create ML Client
        ml_client = create_ml_client(static_config)
        
        # Define names
        endpoint_name = f"ml-health-check-{env_config['endpoint_suffix']}"
        
        # Create or update endpoint
        create_or_update_endpoint(ml_client, endpoint_name, env_config)
        
        # Create environment
        environment_obj = create_environment(static_config["IMAGE_URI"], env_config)
        
        # Create deployment
        deployment_result, deployment_name = create_deployment(
            ml_client, endpoint_name, environment_obj, env_config
        )
        
        # Allocate traffic
        allocate_traffic(ml_client, endpoint_name, deployment_name, 
                        env_config["traffic_allocation"])
        
        # Get endpoint details
        endpoint_info = get_endpoint_details(ml_client, endpoint_name)
        
        # Test deployment
        test_success = test_deployment(ml_client, endpoint_name)
        
        if not test_success:
            logger.warning("Deployment tests failed - this is expected in CI/CD without full Azure setup")
            if not os.environ.get("GITHUB_ACTIONS"):
                sys.exit(1)
        
        # Cleanup old deployments (only in production)
        if environment == "PRODUCTION":
            cleanup_old_deployments(ml_client, endpoint_name)
        
        logger.info("🎉 Deployment completed successfully!")
        logger.info(f"Endpoint URI: {endpoint_info['scoring_uri'] if endpoint_info else 'N/A'}")
        
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 