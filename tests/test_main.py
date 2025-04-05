"""main.pyのテスト"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call

from prcb_checks.main import (
    get_full_repository_name,
    get_secret_value,
    get_access_token,
    create_check_runs,
    main,
)


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
        from botocore.exceptions import ClientError

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

    @patch.dict(os.environ, {})
    def test_missing_keys_of_dict(self):
        """環境変数が設定されていない場合のエラー処理"""
        with pytest.raises(SystemExit) as excinfo:
            get_secret_value("invalid-secret-id")


class TestGetAccessToken:
    """get_access_token関数のテスト"""

    def test_get_access_token(self, mock_jwt, mock_requests, mock_environ):
        """アクセストークンの取得が成功するケース"""
        mock_post, mock_response = mock_requests

        # テスト実行
        result = get_access_token(b"mock-private-key")

        # JWTが正しく生成されていることを確認
        mock_jwt.assert_called_once()
        assert mock_jwt.call_args[0][1] == "mock-private-key"

        # GitHubのAPIが正しく呼び出されていることを確認
        expected_url = "https://api.github.com/app/installations/67890/access_tokens"
        mock_post.assert_called_once()
        assert mock_post.call_args[0][0] == expected_url
        assert (
            mock_post.call_args[1]["headers"]["Authorization"]
            == "Bearer mock-jwt-token"
        )

        # 戻り値が期待通りであることを確認
        assert result == "mock-token"

    @patch.dict(os.environ, {})
    def test_missing_keys_of_dict(self):
        """環境変数が設定されていない場合のエラー処理"""
        with pytest.raises(SystemExit) as excinfo:
            get_access_token(b"mock-private-key")


class TestCreateCheckRuns:
    """create_check_runs関数のテスト"""

    def test_create_check_runs_minimal(self, mock_requests, mock_environ):
        """最小限のパラメータでチェックランを作成するケース"""
        mock_post, mock_response = mock_requests

        # テスト実行
        create_check_runs("mock-access-token", "test-check")

        # GitHubのAPIが正しく呼び出されていることを確認
        expected_url = "https://api.github.com/repos/test-owner/test-repo/check-runs"
        mock_post.assert_called_once()
        assert mock_post.call_args[0][0] == expected_url

        # ヘッダーの確認
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer mock-access-token"
        assert headers["Accept"] == "application/vnd.github+json"

        # ペイロードの確認
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["head_sha"] == "abcdef1234567890"
        assert "status" not in payload
        assert "conclusion" not in payload
        assert "output" not in payload

    def test_create_check_runs_complete(self, mock_requests, mock_environ):
        """すべてのパラメータを指定してチェックランを作成するケース"""
        mock_post, mock_response = mock_requests

        # テスト実行
        create_check_runs(
            "mock-access-token",
            "test-check",
            status="completed",
            conclusion="success",
            title="Test Title",
            summary="Test Summary",
            text="Test Text",
        )

        # ペイロードの確認
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["status"] == "completed"
        assert payload["conclusion"] == "success"
        assert payload["output"]["title"] == "Test Title"
        assert payload["output"]["summary"] == "Test Summary"
        assert payload["output"]["text"] == "Test Text"

    def test_create_check_runs_non_complete(self, mock_requests, mock_environ):
        """すべてのパラメータを指定してチェックランを作成するケース"""
        mock_post, mock_response = mock_requests

        # テスト実行
        create_check_runs(
            "mock-access-token",
            "test-check",
            status="completed",
            conclusion="success",
            summary="Test Summary",
            text="Test Text",
        )

        # ペイロードの確認
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["status"] == "completed"
        assert payload["conclusion"] == "success"
        assert "output" not in payload

    def test_create_check_runs_error_response(self, mock_requests, mock_environ):
        """APIがエラーを返すケース"""
        mock_post, mock_response = mock_requests

        # エラーのモックレスポンスを設定
        mock_response.status_code = 422
        mock_response.json.return_value = {"message": "Validation failed"}

        # テスト実行（例外は発生しないが、エラーログが出力される）
        create_check_runs("mock-access-token", "test-check")

        # API呼び出しが行われていることを確認
        mock_post.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "CODEBUILD_INITIATOR": "GitHub-Hookshot/abcdef",
            "CODEBUILD_SRC_DIR": "/path/to/github.com/test-owner/test-repo",
        },
    )
    def test_missing_keys_of_dict(self, mock_requests):
        """環境変数が設定されていない場合のエラー処理"""
        with pytest.raises(SystemExit) as excinfo:
            create_check_runs(
                "mock-access-token",
                "test-check",
                status="completed",
                conclusion="success",
                title="Test Title",
                summary="Test Summary",
                text="Test Text",
            )


class TestMainFunction:
    """main関数のテスト"""

    @patch(
        "sys.argv",
        [
            "prcb-checks",
            "test-check",
            "completed",
            "success",
            "Test Title",
            "Test Summary",
            "Test Text",
        ],
    )
    def test_main_with_all_arguments(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests
    ):
        """すべての引数が指定された場合のメイン関数のテスト"""
        mock_post, _ = mock_requests

        # テスト実行
        main()

        # シークレットが取得されていることを確認
        mock_boto3_client.get_secret_value.assert_called_once_with(
            SecretId="github-app-private-key"
        )

        # チェックランの作成が正しく呼び出されていることを確認
        mock_post.assert_called()
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["status"] == "completed"
        assert payload["conclusion"] == "success"
        assert payload["output"]["title"] == "Test Title"
        assert payload["output"]["summary"] == "Test Summary"
        assert payload["output"]["text"] == "Test Text"

    @patch("sys.argv", ["prcb-checks", "test-check", "queued"])
    def test_main_with_minimal_arguments(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests
    ):
        """最小限の引数が指定された場合のメイン関数のテスト"""
        mock_post, _ = mock_requests

        # テスト実行
        main()

        # チェックランの作成が正しく呼び出されていることを確認
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["status"] == "queued"
        assert "conclusion" not in payload
        assert "output" not in payload

    @patch("sys.argv", ["prcb-checks", "test-check", "queued", None, "Test Title"])
    def test_main_with_some_none_arguments(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests
    ):
        """一部の引数がNoneの場合のメイン関数のテスト"""
        mock_post, _ = mock_requests

        # テスト実行
        main()

        # チェックランの作成が正しく呼び出されていることを確認
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["status"] == "queued"
        assert "conclusion" not in payload
        assert payload["output"]["title"] == "Test Title"

    @patch("sys.argv", ["prcb-checks"])
    def test_main_with_some_none_arguments(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests
    ):
        """引数が不足している場合のメイン関数のテスト"""
        mock_post, _ = mock_requests

        # テスト実行
        with pytest.raises(SystemExit) as excinfo:
            main()


class TestEnvironmentInitialization:
    """環境変数の初期化処理のテスト"""

    @patch.dict(
        os.environ,
        {
            "CODEBUILD_INITIATOR": "codepipeline/test-pipeline",
            "CODEPIPELINE_FULL_REPOSITORY_NAME": "test-owner/test-repo",
        },
    )
    def test_codepipeline_initiator(self):
        """CodePipelineから呼び出された場合の処理"""
        assert get_full_repository_name() == "test-owner/test-repo"

    @patch.dict(
        os.environ,
        {
            "CODEBUILD_INITIATOR": "GitHub-Hookshot/abcdef",
            "CODEBUILD_SRC_DIR": "/path/to/github.com/test-owner/test-repo",
        },
    )
    def test_github_hookshot_initiator(self):
        """GitHub Hookshotから呼び出された場合の処理"""
        assert get_full_repository_name() == "test-owner/test-repo"

    @patch.dict(os.environ, {"CODEBUILD_INITIATOR": "unknown-initiator"})
    def test_unsupported_initiator(self):
        """未対応のイニシエータの場合のエラー処理"""
        with pytest.raises(SystemExit) as excinfo:
            get_full_repository_name()

        assert excinfo.value.code == 1

    @patch.dict(os.environ, {"CODEBUILD_INITIATOR": "codepipeline/test-pipeline"})
    def test_missing_repository_name(self):
        """環境変数が設定されていない場合のエラー処理"""
        with pytest.raises(SystemExit) as excinfo:
            get_full_repository_name()

        assert excinfo.value.code == 1
