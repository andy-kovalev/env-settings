import pytest
from src.env_settings.config import ErrorHandling, config as global_config


# Тесты для класса ErrorHandling
def test_error_handling_enum_values():
    """Проверка значений перечисления"""
    assert ErrorHandling.EXIT.value == 'exit'
    assert ErrorHandling.RAISE.value == 'raise'
    assert ErrorHandling.PRINT.value == 'print'
    assert ErrorHandling.IGNORE.value == 'ignore'


@pytest.mark.parametrize('value, expected', [
    ('exit', ErrorHandling.EXIT),
    ('raise', ErrorHandling.RAISE),
    ('print', ErrorHandling.PRINT),
    ('ignore', ErrorHandling.IGNORE),
    (ErrorHandling.EXIT, ErrorHandling.EXIT),
    (ErrorHandling.RAISE, ErrorHandling.RAISE)
])
def test_error_handling_from_value_valid(value, expected):
    """Проверка корректных преобразований значений"""
    result = ErrorHandling.from_value(value)
    assert result == expected


@pytest.mark.parametrize('invalid_value', ['invalid', '', None, 123, True, ('exit',)])
def test_error_handling_from_value_invalid(invalid_value):
    """Проверка обработки недопустимых значений"""
    with pytest.raises(ValueError):
        ErrorHandling.from_value(invalid_value)


def test_error_handling_str_representation():
    """Проверка строкового представления"""
    assert str(ErrorHandling.EXIT) == 'exit'
    assert str(ErrorHandling.RAISE) == 'raise'


# Тесты для класса _Config
def test_default_config_values():
    """Проверка значений конфигурации по умолчанию"""
    assert global_config.error_handling == ErrorHandling.RAISE

    messages = global_config.messages
    assert 'err_required' in messages
    assert 'err_integer' in messages
    assert 'err_file' in messages
    assert 'err_directory' in messages

    assert global_config.env_generator_pattern == (
        r'^(?:\s*(?:#.*)?\s*[\r\n]+)*\s*[A-Z0-9_-]+\s*=\s.*?param.*?\(.*?\).*$')


def test_configure_messages():
    """Обновление сообщений об ошибках"""
    test_required_message = 'Custom required message'
    test_new_type_message = 'New error type message'
    test_messages = {
        'err_required': test_required_message,
        'new_type': test_new_type_message
    }

    # Частичное обновление
    global_config.configure(messages=test_messages)

    # Проверка обновленных значений
    assert global_config.messages['err_required'] == test_required_message
    assert global_config.messages['new_type'] == test_new_type_message

    # Проверка сохранения других значений
    assert 'err_integer' in global_config.messages
    assert global_config.messages['err_integer'].startswith('settings: Ошибка загрузки настроек!')


def test_configure_error_handling():
    """Обновление обработки ошибок"""
    # Обновление строкой
    global_config.configure(error_handling='exit')
    assert global_config.error_handling == ErrorHandling.EXIT

    # Обновление значением enum
    global_config.configure(error_handling=ErrorHandling.PRINT)
    assert global_config.error_handling == ErrorHandling.PRINT


def test_configure_env_generator_pattern():
    """Обновление шаблона генератора env-файлов"""
    new_pattern = r'new_pattern'
    global_config.configure(env_generator_pattern=new_pattern)
    assert global_config.env_generator_pattern == new_pattern


def test_configure_invalid_messages_type():
    """Проверка обработки неверного типа для messages"""
    with pytest.raises(TypeError, match='messages должен быть словарем'):
        global_config.configure(messages='invalid type')


def test_configure_invalid_error_handling():
    """Проверка обработки недопустимых значений error_handling"""
    with pytest.raises(ValueError):
        global_config.configure(error_handling='invalid_value')


def test_reset_config():
    """Проверка сброса конфигурации"""
    # Изменяем конфигурацию
    global_config.configure(messages={'err_required': 'Custom'}, error_handling='print',
                            env_generator_pattern='new_pattern')

    # Сбрасываем
    global_config.reset()

    # Проверяем возврат к значениям по умолчанию
    assert global_config.error_handling == ErrorHandling.RAISE
    assert global_config.messages['err_required'].startswith('settings:')
    assert global_config.env_generator_pattern != 'new_pattern'


def test_multiple_config_updates():
    """Проверка последовательных обновлений конфигурации"""
    # Первое обновление
    global_config.configure(error_handling='exit')
    assert global_config.error_handling == ErrorHandling.EXIT

    # Второе обновление
    global_config.configure(env_generator_pattern='pattern_v2')
    assert global_config.env_generator_pattern == 'pattern_v2'

    # Проверка что первое значение сохранилось
    assert global_config.error_handling == ErrorHandling.EXIT


def test_partial_configure():
    """Частичное обновление конфигурации"""
    original_pattern = global_config.env_generator_pattern
    original_messages = global_config.messages.copy()

    # Обновляем только error_handling
    global_config.configure(error_handling='ignore')

    assert global_config.error_handling == ErrorHandling.IGNORE
    assert global_config.env_generator_pattern == original_pattern
    assert global_config.messages == original_messages


# Тесты для синглтона
def test_config_singleton_behavior():
    """Проверка поведения синглтона"""
    from src.env_settings.config import config as config1
    from src.env_settings.config import config as config2

    # Это должен быть один и тот же объект
    assert config1 is config2

    # Изменения в одном экземпляре видны в другом
    config1.configure(error_handling='print')
    assert config2.error_handling == ErrorHandling.PRINT
