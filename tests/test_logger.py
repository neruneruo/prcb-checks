import pytest
import logging
from unittest.mock import patch
from prcb_checks.logger import logger, set_debug_mode


def test_set_debug_mode_enabled():
    # デバッグモード有効時のレベル設定
    set_debug_mode(True)
    assert logger.level == logging.DEBUG


def test_set_debug_mode_disabled():
    # デバッグモード無効時のレベル設定
    set_debug_mode(False)
    assert logger.level == logging.INFO


@patch("logging.Logger.debug")
def test_logger_debug(mock_debug):
    # デバッグメッセージが正しく呼び出されるか
    logger.debug("Test debug message")
    mock_debug.assert_called_once_with("Test debug message")


@patch("logging.Logger.info")
def test_logger_info(mock_info):
    # 情報メッセージが正しく呼び出されるか
    logger.info("Test info message")
    mock_info.assert_called_once_with("Test info message")


@patch("logging.Logger.error")
def test_logger_error(mock_error):
    # エラーメッセージが正しく呼び出されるか
    logger.error("Test error message")
    mock_error.assert_called_once_with("Test error message")
