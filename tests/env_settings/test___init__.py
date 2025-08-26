import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_settings_config(monkeypatch):
    """Фикстура для мока settings_config"""
    mock = MagicMock()
    monkeypatch.setattr('src.env_settings.settings_config', mock)
    return mock


def test_configure_with_empty_params(mock_settings_config):
    """Тест для функции configure, проверка вызова"""
    from src.env_settings import configure

    configure()
    mock_settings_config.configure.assert_called_once_with()


def test_configure_calls_settings_config(mock_settings_config):
    """Тест для функции configure, проверка передачи параметров"""
    from src.env_settings import configure

    test_params = {
        'error_messages': {
            'required': 'Custom required message',
            'integer': 'Custom integer message'
        },
        'error_handling': 'custom_handling'
    }

    configure(**test_params)
    mock_settings_config.configure.assert_called_once_with(**test_params)


@pytest.mark.parametrize('params', [
    {},
    {'option1': 'value1'},
    {'setting1': True, 'setting2': 42}
])
def test_configure_with_different_parameters(mock_settings_config, params):
    """Тест для функции configure, проверка обработки параметров"""
    from src.env_settings import configure

    configure(**params)
    mock_settings_config.configure.assert_called_once_with(**params)


def test_reset_config_calls_settings_reset(mock_settings_config):
    """Тест для функции reset_config, проверка вызова"""
    from src.env_settings import reset_config

    reset_config()
    mock_settings_config.reset.assert_called_once()


def test_module_exports():
    """"Тест для проверки экспортируемых объектов"""
    from src.env_settings import (
        configure,
        reset_config,
        generate_env_file,
        get_str_env_param,
        get_int_env_param,
        get_float_env_param,
        get_bool_env_param,
        get_file_env_param,
        get_filedir_env_param,
        get_value_from_string,
        get_values_from_file,
        get_values,
        endless_param_iterator,
        param_iterator,
        load_env_params
    )

    # Проверяем что импорт работает
    assert callable(configure)
    assert callable(reset_config)
    assert callable(generate_env_file)
    assert callable(get_str_env_param)
    assert callable(get_int_env_param)
    assert callable(get_float_env_param)
    assert callable(get_bool_env_param)
    assert callable(get_file_env_param)
    assert callable(get_filedir_env_param)
    assert callable(get_value_from_string)
    assert callable(get_values_from_file)
    assert callable(get_values)
    assert callable(endless_param_iterator)
    assert callable(param_iterator)
    assert callable(load_env_params)
