"""GitHub client module for authentication and API operations."""

import os
import sys
import time
import requests
import jwt

from prcb_checks.logger import logger
from prcb_checks.repository import get_full_repository_name


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
    annotations=None,
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
        if annotations is not None:
            if "output" in check_run_payload:
                check_run_payload["output"]["annotations"] = annotations

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