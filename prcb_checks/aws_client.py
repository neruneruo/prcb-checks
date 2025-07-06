"""AWS client module for handling Secrets Manager operations."""

import os
import sys
import boto3
from botocore.exceptions import ClientError

from prcb_checks.logger import logger


def get_secrets_manager_client():
    """Get AWS Secrets Manager client"""
    try:
        session = boto3.session.Session()
        return session.client(
            service_name="secretsmanager",
            region_name=os.environ["AWS_REGION"],
        )
    except KeyError as e:
        logger.error(f"Error: Required environment variable not found: {e}")
        sys.exit(1)


def get_secret_value(secret_id):
    """Get secret value from AWS Secrets Manager"""
    try:
        client = get_secrets_manager_client()
        response = client.get_secret_value(SecretId=secret_id)
        return response["SecretBinary"]
    except ClientError as e:
        logger.error(f"get_secret_value() error: {e}")
        raise e