from unittest.mock import MagicMock

import pytest

from src.env_settings.config import config as global_config


@pytest.fixture(autouse=True)
def reset_config():
    """Фикстура для изоляции тестов, сбрасывает конфиг после каждого теста"""
    yield
    global_config.reset()


@pytest.fixture
def mock_settings_config(monkeypatch):
    """Фикстура для мока settings_config"""
    mock = MagicMock()
    monkeypatch.setattr('src.env_settings.settings_config', mock)
    return mock
