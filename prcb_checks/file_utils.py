"""File utilities module for reading and parsing files."""

import json
import sys

from prcb_checks.logger import logger


def read_file_content(file_path):
    """
    Read file content from a file path
    Args:
        file_path (str): Path of the file to read
    Returns:
        str: Content of the file
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        sys.exit(1)


def parse_json_file(file_path):
    """
    Parse JSON content from a file
    Args:
        file_path (str): Path of the JSON file to read
    Returns:
        dict/list: Parsed JSON content
    """
    try:
        content = read_file_content(file_path)
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON in file {file_path}: {e}")
        sys.exit(1)