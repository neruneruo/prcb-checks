"""テスト用の共通フィクスチャを定義するファイル"""

import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_environ():
    """テスト用の環境変数のモック"""
    with patch.dict(
        os.environ,
        {
            "GITHUB_APP_ID": "12345",
            "GITHUB_APP_INSTALLATION_ID": "67890",
            "CODEBUILD_INITIATOR": "codepipeline/test-pipeline",
            "CODEPIPELINE_FULL_REPOSITORY_NAME": "test-owner/test-repo",
            "CODEBUILD_RESOLVED_SOURCE_VERSION": "abcdef1234567890",
            "AWS_REGION": "us-east-1",
            "SECRETS_MANAGER_SECRETID": "github-app-private-key",
        },
    ):
        yield


@pytest.fixture
def mock_boto3_client():
    """AWS Secrets Managerクライアントのモック"""
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {"SecretBinary": b"mock-private-key"}

    with patch("boto3.session.Session") as mock_session:
        mock_session.return_value.client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_requests():
    """requestsモジュールのモック"""
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        # デフォルトのモックレスポンス設定
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "mock-token",
            "id": 12345,
            "url": "https://api.github.com/repos/test-owner/test-repo/check-runs/12345",
        }

        yield mock_post, mock_response


@pytest.fixture
def mock_jwt():
    """PyJWTモジュールのモック"""
    with patch("jwt.encode") as mock_encode:
        mock_encode.return_value = "mock-jwt-token"
        yield mock_encode
