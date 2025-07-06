"""aws_client.pyのテスト"""

import os
import pytest
from unittest.mock import patch
from botocore.exceptions import ClientError

from prcb_checks.aws_client import get_secret_value


class TestGetSecretValue:
    """get_secret_value関数のテスト"""

    def test_get_secret_value_success(self, mock_boto3_client, mock_environ):
        """シークレット値の取得が成功するケース"""
        result = get_secret_value("test-secret-id")

        # Secrets Managerが正しく呼び出されていることを確認
        mock_boto3_client.get_secret_value.assert_called_once_with(
            SecretId="test-secret-id"
        )

        # 戻り値が期待通りであることを確認
        assert result == b"mock-private-key"

    def test_get_secret_value_error(self, mock_boto3_client, mock_environ):
        """シークレット値の取得がエラーになるケース"""
        # エラーが発生するように設定
        mock_boto3_client.get_secret_value.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": "Secret not found",
                }
            },
            "GetSecretValue",
        )

        # 例外が発生することを確認
        with pytest.raises(ClientError):
            get_secret_value("invalid-secret-id")

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_keys_of_dict(self):
        """環境変数が設定されていない場合のエラー処理"""
        with pytest.raises(SystemExit) as excinfo:
            get_secret_value("invalid-secret-id")