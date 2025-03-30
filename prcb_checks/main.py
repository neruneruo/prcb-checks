"""checkruns.py - GitHub Checks APIを実行する"""

# https://docs.github.com/ja/rest/checks/runs?apiVersion=2022-11-28#create-a-check-run
# checkruns.py <name> <status:conclusion> <title> <summary> <text>
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

import sys
import os
import time

import requests
import boto3
from botocore.exceptions import ClientError
import jwt

# GitHub Appの情報
github_app_id = os.environ["GITHUB_APP_ID"]
github_app_installation_id = os.environ["GITHUB_APP_INSTALLATION_ID"]

# リポジトリの情報
codebuild_initiator = os.environ["CODEBUILD_INITIATOR"]
if codebuild_initiator.startswith("codepipeline/"):
    # AWS CodePipelineから呼び出した場合、パイプラインのステージ環境変数から取得
    full_repository_name = os.environ["CODEPIPELINE_FULL_REPOSITORY_NAME"]
elif codebuild_initiator.startswith("GitHub-Hookshot/"):
    # AWS CodeBuildから呼び出した場合、"github.com/" で分割し、右側の部分（可変部分）を取得
    _, _, full_repository_name = os.environ["CODEBUILD_SRC_DIR"].rpartition(
        "github.com/"
    )
else:
    print(f"Error: Unsupported CODEBUILD_INITIATOR: {codebuild_initiator}")
    sys.exit(1)

# AWS Secrets Managerのシークレット取得
session = boto3.session.Session()
client = session.client(
    service_name="secretsmanager",
    region_name=os.environ["AWS_REGION"],
)


def get_secret_value(secret_id):
    """AWS Secrets Managerからシークレットを取得する"""
    try:
        response = client.get_secret_value(SecretId=secret_id)
        return response["SecretBinary"]
    except ClientError as e:
        print(f"get_secret_value() error: {e}")
        raise e


def get_access_token(private_key):
    """JWTアクセストークンをGitHubリクエストして取得する"""
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
        check_run_payload["output"]["summary"] = summary
    if text is not None:
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
        print("チェックランの作成に成功しました。")
        print(response.json())
    else:
        print(f"エラーが発生しました: {response.status_code}")
        print(response.json())


def main():
    """メイン処理"""
    private_key = get_secret_value(os.environ["SECRETS_MANAGER_SECRETID"])
    access_token = get_access_token(private_key)

    kwargs = {}
    kwargs["name"] = sys.argv[1]
    if sys.argv[2] is not None:
        kwargs["status"] = sys.argv[2]
    if len(sys.argv) > 3 and sys.argv[3]:
        kwargs["conclusion"] = sys.argv[3]
    if len(sys.argv) > 4 and sys.argv[4]:
        kwargs["title"] = sys.argv[4]
    if len(sys.argv) > 5 and sys.argv[5]:
        kwargs["summary"] = sys.argv[5]
    if len(sys.argv) > 6 and sys.argv[6]:
        kwargs["text"] = sys.argv[6]

    create_check_runs(access_token, **kwargs)


if __name__ == "__main__":
    main()
