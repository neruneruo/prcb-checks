"""main.pyのテスト"""

import os
import sys
import pytest
import json
from unittest.mock import patch

from prcb_checks.main import main


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


