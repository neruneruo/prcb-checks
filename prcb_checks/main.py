"""PRCB checks - Invoke GitHub Checks API"""

# https://docs.github.com/ja/rest/checks/runs?apiVersion=2022-11-28#create-a-check-run
# checkruns.py <n> <status:conclusion> <title> <summary> <text>
# name      : The name of the check. For example, "code-coverage".
# status    : The current status of the check run. Only GitHub Actions can set a status of waiting, pending, or requested.
#             Default: queue
#             You can set queued, in_progress, completed, waiting, requested, pending
# conclusion: Required if you provide completed_at or a status of completed. The final conclusion of the check.
#             Note: Providing conclusion will automatically set the status parameter to completed.
#             You cannot change a check run conclusion to stale, only GitHub can set this.
#             You can set action_required, cancelled, failure, neutral, success, skipped, stale, timed_out
# title     : The title of the check run.
# summary   : The summary of the check run. This parameter supports Markdown.
# text      : The details of the check run. This parameter supports Markdown.

import optparse
import os
import time
import sys

import requests
import boto3
from botocore.exceptions import ClientError
import jwt

from prcb_checks.logger import logger, set_debug_mode


def get_full_repository_name():
    """Get GitHub repository info from environment variable"""
    try:
        # リポジトリの情報
        codebuild_initiator = os.environ["CODEBUILD_INITIATOR"]
        if codebuild_initiator.startswith("codepipeline/"):
            # AWS CodePipelineから呼び出した場合、パイプラインのステージ環境変数から取得
            return os.environ["CODEPIPELINE_FULL_REPOSITORY_NAME"]
        elif codebuild_initiator.startswith("GitHub-Hookshot/"):
            # AWS CodeBuildから呼び出した場合、"github.com/" で分割し、右側の部分（可変部分）を取得
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


def get_access_token(private_key):
    """Get JWT access token from GitHub API request"""
    try:
        # GitHub Appの情報
        github_app_id = os.environ["GITHUB_APP_ID"]
        github_app_installation_id = os.environ["GITHUB_APP_INSTALLATION_ID"]

        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),  # 有効期間10分
            "iss": github_app_id,
        }
        jwt_token = jwt.encode(payload, private_key.decode(), algorithm="RS256")

        # インストールアクセストークンの取得
        token_url = f"https://api.github.com/app/installations/{github_app_installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
        }
        response = requests.post(token_url, headers=headers, timeout=60.0)
        return response.json()["token"]
    except KeyError as e:
        logger.error(f"Error: Required environment variable not found: {e}")
        sys.exit(1)


def create_check_runs(
    access_token,
    name,
    status=None,
    conclusion=None,
    title=None,
    summary=None,
    text=None,
):
    """Check Runsを作成する"""
    try:
        full_repository_name = get_full_repository_name()
        check_run_payload = {
            "name": name,
            "head_sha": os.environ["CODEBUILD_RESOLVED_SOURCE_VERSION"],
        }
        if status is not None:
            check_run_payload["status"] = status
        if conclusion is not None:
            check_run_payload["conclusion"] = conclusion
        if title is not None:
            check_run_payload["output"] = {"title": title}
        if summary is not None:
            if "output" in check_run_payload:
                check_run_payload["output"]["summary"] = summary
        if text is not None:
            if "output" in check_run_payload:
                check_run_payload["output"]["text"] = text

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }

        response = requests.post(
            f"https://api.github.com/repos/{full_repository_name}/check-runs",
            headers=headers,
            json=check_run_payload,
            timeout=60.0,
        )

        if response.status_code == 201:
            logger.debug("Succeeded create check-runs.")
            logger.debug(response.json())
        else:
            logger.error(f"Error creating check-runs: {response.status_code}")
            logger.debug(response.json())
    except KeyError as e:
        logger.error(f"Error: Required environment variable not found: {e}")
        sys.exit(1)


def parse_options():
    parser = optparse.OptionParser()
    parser.add_option(
        "-d",
        "--debug",
        dest="debug",
        default=False,
        help="Enable debug mode with verbose output",
    )

    return parser.parse_args()


def main():
    """Main entry point."""

    options, args = parse_options()

    set_debug_mode(options.debug)

    try:
        private_key = get_secret_value(os.environ["SECRETS_MANAGER_SECRETID"])
        access_token = get_access_token(private_key)

        kwargs = {}
        kwargs["name"] = args[0]
        if len(args) > 1 and args[1]:
            kwargs["status"] = args[1]
        if len(args) > 2 and args[2]:
            kwargs["conclusion"] = args[2]
        if len(args) > 3 and args[3]:
            kwargs["title"] = args[3]
        if len(args) > 4 and args[4]:
            kwargs["summary"] = args[4]
        if len(args) > 5 and args[5]:
            kwargs["text"] = args[5]

        create_check_runs(access_token, **kwargs)
    except IndexError:
        logger.error("Error: Not enough arguments provided.")
        logger.info(
            "Usage: %prog <name> <status> [conclusion] [title] [summary] [text]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()  # pragma: no cover
