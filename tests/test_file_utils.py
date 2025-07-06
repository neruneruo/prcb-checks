"""file_utils.pyのテスト"""

import json
import pytest
from unittest.mock import patch

from prcb_checks.file_utils import parse_json_file, read_file_content


class TestReadFileContent:
    """ファイル読み込み機能のテスト"""

    def test_read_file_content(self, tmp_path):
        # テスト用のファイルを作成
        test_file = tmp_path / "test_content.txt"
        test_content = "This is a test content\nwith multiple lines\nfor testing."
        test_file.write_text(test_content)

        # ファイル読み込み関数をテスト
        result = read_file_content(str(test_file))

        assert result == test_content

    @patch("sys.exit")
    def test_read_file_content_exception(self, mock_exit, tmp_path):
        """ファイル読み込み例外のテスト"""
        # 存在しないファイルパスを指定
        non_existent_file = tmp_path / "non_existent_file.txt"

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