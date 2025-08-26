import os
from pathlib import Path
from unittest.mock import patch, mock_open, call

import pytest

from src.env_settings.config import config
from src.env_settings.generator import _get_settings_values, generate_env_file


# Фикстура для временной структуры файлов
@pytest.fixture
def setup_files(tmp_path):
    # Создаем корневую директорию
    root = tmp_path / 'project'
    root.mkdir()

    # Создаем файл настроек в корне
    settings_file = root / 'settings.py'
    settings_content = """
# Database settings
# Hostname
DB_HOST = get_str_env_param('DB_HOST', default='localhost')
# Port
DB_PORT = get_int_env_param('DB_PORT', default=5432)

# API settings
API_KEY = get_str_env_param('API_KEY')
"""
    settings_file.write_text(settings_content)

    # Создаем поддиректории с файлами настроек
    modules = root / 'modules'
    modules.mkdir()

    # Модуль auth
    auth = modules / 'auth'
    auth.mkdir()
    auth_settings = auth / 'settings.py'
    auth_settings.write_text("AUTH_SECRET = get_str_env_param('secret123')")

    # Модуль payment
    payment = modules / 'payment'
    payment.mkdir()
    payment_settings = payment / 'settings.py'
    payment_settings.write_text("PAYMENT_KEY = get_str_env_param('pay_key')")

    # Модуль excluded
    excluded = modules / 'excluded'
    excluded.mkdir()
    excluded_settings = excluded / 'settings.py'
    excluded_settings.write_text("EXCLUDED_PARAM = get_str_env_param('value')")

    return root


# Тесты для _get_settings_values
def test_get_settings_values_basic(setup_files):
    settings_file = setup_files / 'settings.py'
    result = _get_settings_values(str(settings_file))

    assert len(result) == 3
    assert 'DB_HOST=' in result[0]
    assert 'DB_PORT=' in result[1]
    assert 'API_KEY=' in result[2]


def test_get_settings_values_with_exclusion(setup_files):
    settings_file = setup_files / 'settings.py'
    result = _get_settings_values(str(settings_file), exclude_params=('DB_HOST',))

    assert len(result) == 2
    assert 'DB_HOST=' not in result[0]
    assert 'DB_PORT=' in result[0]
    assert 'API_KEY=' in result[1]


def test_get_settings_values_with_custom_pattern(setup_files):
    settings_file = setup_files / 'settings.py'

    config.configure(env_generator_pattern=r'^.*API_KEY.*$')
    try:
        result = _get_settings_values(str(settings_file))
    finally:
        config.reset()

    assert len(result) == 1
    assert 'API_KEY=' in result[0]


def test_get_settings_values_empty_file(tmp_path):
    empty_file = tmp_path / 'empty.py'
    empty_file.write_text("")
    result = _get_settings_values(str(empty_file))
    assert len(result) == 0


def test_get_settings_values_no_matches(tmp_path):
    no_match_file = tmp_path / 'no_match.py'
    no_match_file.write_text("variable = 'value'")
    result = _get_settings_values(str(no_match_file))
    assert len(result) == 0


# Тесты для generate_env_file
def test_generate_env_file_basic(setup_files, tmp_path):
    env_file = tmp_path / '.env'
    generate_env_file(new_env_filename=str(env_file), settings_filename='settings.py', modules_path=str(setup_files))

    content = env_file.read_text()
    assert 'DB_HOST=' in content
    assert 'DB_PORT=' in content
    assert 'API_KEY=' in content
    assert content.count('\n') == 15  # 6 параметров + 4 комментария + 5 отступов (последний параметр без отступа)


def test_generate_env_file_with_submodules(setup_files, tmp_path):
    env_file = tmp_path / '.env'
    generate_env_file(new_env_filename=str(env_file), settings_filename='settings.py', modules_path=str(setup_files),
                      sub_modules_path='modules', include_sub_modules=('auth', 'payment'))

    content = env_file.read_text()
    assert 'DB_HOST=' in content  # из корня
    assert 'AUTH_SECRET=' in content
    assert 'PAYMENT_KEY=' in content
    assert 'EXCLUDED_PARAM=' not in content


def test_generate_env_file_with_exclusion(setup_files, tmp_path):
    env_file = tmp_path / '.env'
    generate_env_file(new_env_filename=str(env_file), settings_filename='settings.py', modules_path=str(setup_files),
                      exclude_params=('DB_HOST', 'API_KEY'))

    content = env_file.read_text()
    assert 'DB_HOST=' not in content
    assert 'DB_PORT=' in content
    assert 'API_KEY=' not in content


def test_generate_env_file_empty_output(setup_files, tmp_path):
    env_file = tmp_path / '.env'
    generate_env_file(new_env_filename=str(env_file), settings_filename='settings.py', modules_path=str(setup_files),
                      include_sub_modules=('None'), exclude_params=('DB_HOST', 'DB_PORT', 'API_KEY'))

    content = env_file.read_text()
    assert content == ""


def test_generate_env_file_complex_structure(setup_files, tmp_path):
    # Добавим еще один уровень вложенности
    deep_module = setup_files / 'modules' / 'deep' / 'deeper'
    deep_module.mkdir(parents=True)
    deep_settings = deep_module / 'settings.py'
    deep_settings.write_text("DEEP_PARAM = get_str_env_param('deep_value')")

    env_file = tmp_path / '.env'
    generate_env_file(new_env_filename=str(env_file), settings_filename='settings.py', modules_path=str(setup_files),
                      sub_modules_path='modules', include_sub_modules=('deep',))

    content = env_file.read_text()
    assert 'DEEP_PARAM=' in content


# Тест с моком для изоляции файловой системы
@patch('builtins.open', new_callable=mock_open)
@patch('pathlib.Path.walk')
def test_generate_env_file_calls(mock_walk, mock_open, tmp_path):
    # Настраиваем моки
    mock_walk.return_value = [(Path('project'), ['subdir'], ['settings.py'])]

    # Мок для _get_settings_values
    with patch('src.env_settings.generator._get_settings_values') as mock_get:
        mock_get.return_value = ['PARAM1=\n', 'PARAM2=\n']

        generate_env_file(new_env_filename='.env', settings_filename='settings.py', modules_path='project')

    # Проверяем вызовы
    mock_walk.assert_called_once()
    mock_get.assert_called_once_with(os.path.join(os.path.curdir, 'project', 'settings.py'), None)

    # Проверяем запись в файл
    mock_open.assert_called_once_with('.env', mode='w', encoding='utf-8')
    handle = mock_open()
    handle.write.assert_has_calls([call('PARAM1=\n\n'), call('PARAM2=\n')])


# Тест для проверки форматирования вывода
def test_generate_env_file_formatting(setup_files, tmp_path):
    env_file = tmp_path / '.env'
    generate_env_file(new_env_filename=str(env_file), settings_filename='settings.py', modules_path=str(setup_files),
                      include_sub_modules=('None'), exclude_params=('DB_PORT', 'API_KEY'))

    content = env_file.read_text().split('\n')
    # Проверяем что в конце файла нет лишнего переноса
    assert len(content) == 4
    assert content[2] == 'DB_HOST='
    assert content[3] == ''
