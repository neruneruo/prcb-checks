"""main.pyのテスト"""

import os
import sys
import pytest
import json
from unittest.mock import patch, MagicMock, call

from prcb_checks.main import (
    get_full_repository_name,
    get_secret_value,
    get_access_token,
    create_check_runs,
    parse_json_file,
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
            '[{"path": "src/main.py", "start_line": 10, "end_line": 10, "annotation_level": "warning", "message": "Test Message"}]',
        ],
    )
    def test_main_with_annotations_json(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests
    ):
        """アノテーションJSON文字列を含むメイン関数のテスト"""
        mock_post, _ = mock_requests

        # テスト実行
        main()

        # チェックランの作成が正しく呼び出されていることを確認
        mock_post.assert_called()
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["output"]["annotations"] == [
            {
                "path": "src/main.py",
                "start_line": 10,
                "end_line": 10,
                "annotation_level": "warning",
                "message": "Test Message",
            }
        ]

    def test_main_with_all_arguments_with_file(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests, tmp_path
    ):
        """すべての引数が指定された場合のメイン関数のテスト(textはfile://プレフィックス)"""
        # テスト用のファイルを作成
        test_file = tmp_path / "check_content.txt"
        test_content = (
            "## Test Report\n\nThis is a detailed report with **markdown** formatting."
        )
        test_file.write_text(test_content)

        mock_post, _ = mock_requests

        # テスト実行
        with patch.object(
            sys,
            "argv",
            [
                "prcb-checks",
                "test-check",
                "completed",
                "success",
                "Test Title",
                "Test Summary",
                f"file://{test_file}",
            ],
        ):
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
        assert payload["output"]["text"] == test_content

    def test_main_with_annotations_from_file(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests, tmp_path
    ):
        """ファイルからアノテーションを読み込むメイン関数のテスト"""
        # テスト用のアノテーションJSONファイルを作成
        test_file = tmp_path / "annotations.json"
        test_annotations = [
            {
                "path": "src/main.py",
                "start_line": 42,
                "end_line": 42,
                "annotation_level": "warning",
                "message": "Variable foo is not used",
                "title": "Unused Variable",
            }
        ]
        test_file.write_text(json.dumps(test_annotations))

        mock_post, _ = mock_requests

        # テスト実行
        with patch.object(
            sys,
            "argv",
            [
                "prcb-checks",
                "test-check",
                "completed",
                "failure",
                "Test Title",
                "Test Summary",
                "Test Text",
                f"file://{test_file}",
            ],
        ):
            main()

        # チェックランの作成が正しく呼び出されていることを確認
        mock_post.assert_called()
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["output"]["annotations"] == test_annotations

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

    @patch(
        "sys.argv",
        [
            "prcb-checks",
            "--debug",
            "test-check",
            "completed",
            "success",
            "Test Title",
            "Test Summary",
            "Test Text",
        ],
    )
    def test_main_with_all_arguments_and_debug(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests
    ):
        """debug mode test"""
        mock_post, _ = mock_requests

        # テスト実行
        main()

        # チェックランの作成が正しく呼び出されていることを確認
        payload = mock_post.call_args[1]["json"]
        assert payload["name"] == "test-check"
        assert payload["status"] == "completed"
        assert payload["conclusion"] == "success"
        assert payload["output"]["title"] == "Test Title"
        assert payload["output"]["summary"] == "Test Summary"
        assert payload["output"]["text"] == "Test Text"

    @patch("sys.argv", ["prcb-checks"])
    def test_main_with_some_none_arguments(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests
    ):
        """引数が不足している場合のメイン関数のテスト"""
        mock_post, _ = mock_requests

        # テスト実行
        with pytest.raises(SystemExit) as excinfo:
            main()

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
            '[{"path": "src/main.py" "start_line": 10, "end_line": 10, "annotation_level": "warning", "message": "Test Message"}]',
        ],
    )
    def test_main_with_annotations_invalid_json(
        self, mock_environ, mock_boto3_client, mock_jwt, mock_requests
    ):
        """アノテーションJSON文字列を含むメイン関数のテスト(JSONパースエラー)"""
        mock_post, _ = mock_requests

        # チェックランの作成が正しく呼び出されていることを確認
        # テスト実行
        with pytest.raises(SystemExit) as excinfo:
            main()


class TestReadFileContent:
    """ファイル読み込み機能のテスト"""

    def test_read_file_content(self, tmp_path):
        # テスト用のファイルを作成
        test_file = tmp_path / "test_content.txt"
        test_content = "This is a test content\nwith multiple lines\nfor testing."
        test_file.write_text(test_content)

        # ファイル読み込み関数をテスト
        from prcb_checks.main import read_file_content

        result = read_file_content(str(test_file))

        assert result == test_content

    @patch("sys.exit")
    def test_read_file_content_exception(self, mock_exit, tmp_path):
        """ファイル読み込み例外のテスト"""
        # 存在しないファイルパスを指定
        non_existent_file = tmp_path / "non_existent_file.txt"

        # モックの設定
        from prcb_checks.main import read_file_content

        # 例外が発生することを確認
        read_file_content(str(non_existent_file))

        # sys.exitが呼び出されたことを確認
        mock_exit.assert_called_once_with(1)


class TestJsonParsing:
    """JSON解析機能のテスト"""

    def test_parse_json_file(self, tmp_path):
        """JSONファイルの解析のテスト"""
        # テスト用のJSONファイルを作成
        test_file = tmp_path / "test.json"
        test_data = {
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
            ]
        }
        test_file.write_text(json.dumps(test_data))

        # 関数のテスト
        result = parse_json_file(str(test_file))
        assert result == test_data

    def test_parse_json_file_invalid(self, tmp_path):
        """不正なJSONファイルの解析のテスト"""
        # 不正なJSON形式のファイルを作成
        test_file = tmp_path / "invalid.json"
        test_file.write_text("This is not valid JSON")

        # 不正なJSONの場合、エラーになることを確認
        with pytest.raises(SystemExit) as excinfo:
            parse_json_file(str(test_file))


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
