"""Repository information handling module."""

import os
import sys

from prcb_checks.logger import logger


def get_full_repository_name():
    """Get GitHub repository info from environment variable"""
    try:
        # リポジトリの情報
        codebuild_initiator = os.environ["CODEBUILD_INITIATOR"]
        if codebuild_initiator.startswith("codepipeline/"):
            # AWS CodePipelineから呼び出した場合、パイプラインのステージ環境変数から取得
            return os.environ["CODEPIPELINE_FULL_REPOSITORY_NAME"]
        elif codebuild_initiator.startswith("GitHub-Hookshot/"):
            # AWS CodeBuildから呼び出した場合、"github.com/" で分割し、後ろの部分（可変部分）を取得
            _, _, full_repository_name = os.environ["CODEBUILD_SRC_DIR"].rpartition(
                "github.com/"
            )
            return full_repository_name
        else:
            logger.error(
                f"Error: Unsupported CODEBUILD_INITIATOR: {codebuild_initiator}"
            )
            sys.exit(1)
    except KeyError as e:
        logger.error(f"Error: Required environment variable not found: {e}")
        sys.exit(1)