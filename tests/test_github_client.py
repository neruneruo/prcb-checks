"""github_client.pyのテスト"""

import os
import pytest
from unittest.mock import patch

from prcb_checks.github_client import get_access_token, create_check_runs


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

    @patch.dict(os.environ, {}, clear=True)
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

    def test_create_check_runs_with_annotations(self, mock_requests, mock_environ):
        """アノテーションを含めてチェックランを作成するケース"""
        mock_post, mock_response = mock_requests

        annotations = [
            {
                "path": "src/main.py",
                "start_line": 42,
                "end_line": 42,
                "annotation_level": "warning",
                "message": "Variable foo is not used",
                "title": "Unused Variable",
            }
        ]

        # テスト実行
        create_check_runs(
            "mock-access-token",
            "test-check",
            status="completed",
            conclusion="failure",
            title="Test Title",
            summary="Test Summary",
            text="Test Text",
            annotations=annotations,
        )

        # ペイロードの確認
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["status"] == "completed"
        assert payload["conclusion"] == "failure"
        assert payload["output"]["title"] == "Test Title"
        assert payload["output"]["summary"] == "Test Summary"
        assert payload["output"]["text"] == "Test Text"
        assert payload["output"]["annotations"] == annotations

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