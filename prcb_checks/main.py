"""PRCB checks - Invoke GitHub Checks API"""

# https://docs.github.com/ja/rest/checks/runs?apiVersion=2022-11-28#create-a-check-run
# checkruns.py <n> <status:conclusion> <title> <summary> <text> [annotations]
# name        : The name of the check. For example, "code-coverage".
# status      : The current status of the check run. Only GitHub Actions can set a status of waiting, pending, or requested.
#                 Default: queue
#                 You can set queued, in_progress, completed, waiting, requested, pending
# conclusion  : Required if you provide completed_at or a status of completed. The final conclusion of the check.
#                 Note: Providing conclusion will automatically set the status parameter to completed.
#                 You cannot change a check run conclusion to stale, only GitHub can set this.
#                 You can set action_required, cancelled, failure, neutral, success, skipped, stale, timed_out
# title       : The title of the check run.
# summary     : The summary of the check run. This parameter supports Markdown.
# text        : The details of the check run. This parameter supports Markdown.
# annotations : JSON array of annotation objects. If starts with file://, read from file.

import json
import optparse
import os
import sys

from prcb_checks.logger import logger, set_debug_mode
from prcb_checks.aws_client import get_secret_value
from prcb_checks.github_client import get_access_token, create_check_runs
from prcb_checks.file_utils import read_file_content, parse_json_file
from prcb_checks.repository import get_full_repository_name

# Backward compatibility imports for existing tests
__all__ = [
    'get_secret_value',
    'get_access_token', 
    'create_check_runs',
    'parse_json_file',
    'get_full_repository_name',
    'main'
]




def parse_options():
    parser = optparse.OptionParser()
    parser.add_option(
        "-d",
        "--debug",
        action="store_true",
        dest="debug",
        default=False,
        help="Enable debug mode with verbose output",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    TEXT_FILE_PREFIX = "file://"

    options, args = parse_options()

    set_debug_mode(options.debug)
    logger.debug(f"ARGS: {args}")

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
            text_arg = args[5]
            if text_arg.startswith(TEXT_FILE_PREFIX):
                # fmt: off
                file_path = text_arg[len(TEXT_FILE_PREFIX):]
                # fmt: on
                kwargs["text"] = read_file_content(file_path)
            else:
                # 通常のテキスト
                kwargs["text"] = text_arg
                
        # Handle annotations parameter if provided
        if len(args) > 6 and args[6]:
            annotations_arg = args[6]
            if annotations_arg.startswith(TEXT_FILE_PREFIX):
                # Read annotations from file
                file_path = annotations_arg[len(TEXT_FILE_PREFIX):]
                annotations = parse_json_file(file_path)
                kwargs["annotations"] = annotations
            else:
                # Parse JSON string directly
                try:
                    kwargs["annotations"] = json.loads(annotations_arg)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing annotations JSON: {e}")
                    sys.exit(1)

        create_check_runs(access_token, **kwargs)
    except IndexError:
        logger.error("Error: Not enough arguments provided.")
        logger.info(
            "Usage: %prog <name> <status> [conclusion] [title] [summary] [text] [annotations]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()  # pragma: no cover