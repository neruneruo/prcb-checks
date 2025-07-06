"""repository.pyのテスト"""

import os
import pytest
from unittest.mock import patch

from prcb_checks.repository import get_full_repository_name


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