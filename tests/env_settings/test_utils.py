import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.env_settings.config import config, ErrorHandling
from src.env_settings.utils import (_env_param_error, _create_directory, get_str_env_param, get_int_env_param,
                                    get_float_env_param, get_bool_env_param, get_file_env_param, get_filedir_env_param,
                                    get_value_from_string, get_values_from_file, get_values, endless_param_iterator,
                                    param_iterator, load_env_params)


# Фикстура для сброса конфигурации перед каждым тестом
@pytest.fixture(autouse=True)
def reset_config():
    yield
    config.reset()


# Фикстура для временной директории
@pytest.fixture
def tmp_env(monkeypatch, tmp_path):
    # Устанавливаем временную директорию
    monkeypatch.setattr('os.getenv', lambda k, d=None: os.environ.get(k, d))
    monkeypatch.setattr('os.path.exists', lambda p: False if p is None else Path(p).exists())
    monkeypatch.setattr('os.path.isfile', lambda p: False if p is None else Path(p).is_file())
    monkeypatch.setattr('os.path.isdir', lambda p: False if p is None else Path(p).is_dir())
    monkeypatch.setattr('os.makedirs', lambda p: Path(p).mkdir(parents=True, exist_ok=True))
    return tmp_path


# Тесты для _env_param_error
@pytest.mark.parametrize("handling, expected",
                         [(ErrorHandling.EXIT, "exit"), (ErrorHandling.RAISE, "raise"), (ErrorHandling.PRINT, "print"),
                          (ErrorHandling.IGNORE, "ignore"), ])
def test_env_param_error(handling, expected, monkeypatch):
    """Тестирование обработки ошибок с разными стратегиями"""
    # Мокируем поведение в зависимости от стратегии
    config.configure(error_handling=handling)

    if handling == ErrorHandling.EXIT:
        with pytest.raises(SystemExit, match="Test error"):
            _env_param_error("Test error")
    elif handling == ErrorHandling.RAISE:
        with pytest.raises(ValueError, match="Test error"):
            _env_param_error("Test error")
    elif handling == ErrorHandling.PRINT:
        with patch('builtins.print') as mock_print:
            _env_param_error("Test error")
            mock_print.assert_called_once_with("Test error")
    else:  # IGNORE
        _env_param_error("Test error")  # Ничего не должно произойти


# Тесты для _create_directory
def test_create_directory_for_file(tmp_env):
    """Создание директории для файла"""
    file_path = tmp_env / "new_dir" / "file.txt"
    _create_directory(str(file_path), is_filename=True)
    assert (tmp_env / "new_dir").exists()


def test_create_directory_for_dir(tmp_env):
    """Создание самой директории"""
    dir_path = tmp_env / "new_directory"
    _create_directory(str(dir_path))
    assert dir_path.exists()


def test_create_existing_directory(tmp_env):
    """Попытка создать существующую директорию (не должно быть ошибки)"""
    dir_path = tmp_env / "existing"
    dir_path.mkdir()
    _create_directory(str(dir_path))
    assert dir_path.exists()


# Тесты для функций получения параметров
class TestGetParams:
    """Тесты для функций get_*_env_param"""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch, tmp_env):
        """Устанавливаем тестовые переменные окружения"""
        monkeypatch.setenv("STR_PARAM", "test_value")
        monkeypatch.setenv("INT_PARAM", "42")
        monkeypatch.setenv("FLOAT_PARAM", "3.14")
        monkeypatch.setenv("BOOL_PARAM_TRUE", "true")
        monkeypatch.setenv("BOOL_PARAM_FALSE", "false")
        monkeypatch.setenv("FILE_PARAM", str(tmp_env / "file.txt"))
        monkeypatch.setenv("DIR_PARAM", str(tmp_env / "directory"))

        # Создаем реальный файл для тестов
        (tmp_env / "file.txt").write_text("content")

        # Настраиваем сообщения об ошибках
        config.configure(error_messages={'required': "Required: %s", 'integer': "Integer error: %s=%s",
                                         'float': "Float error: %s=%s", 'file': "File error: %s=%s",
                                         'directory': "Directory error: %s=%s %s"})

    def test_get_str_env_param(self):
        """Получение строкового параметра"""
        assert get_str_env_param("STR_PARAM") == "test_value"
        assert get_str_env_param("MISSING") is None
        assert get_str_env_param("MISSING", default="default") == "default"

        # Обязательный параметр
        with patch('src.env_settings.utils._env_param_error') as mock_error:
            get_str_env_param("MISSING", required=True)
            mock_error.assert_called_with("Required: MISSING")

    def test_get_int_env_param(self):
        """Получение целочисленного параметра"""
        assert get_int_env_param("INT_PARAM") == 42
        assert get_int_env_param("MISSING", default=100) == 100

        # Невалидное значение
        with patch('src.env_settings.utils._env_param_error') as mock_error:
            get_int_env_param("STR_PARAM")
            mock_error.assert_called_with("Integer error: STR_PARAM=test_value")

    def test_get_float_env_param(self):
        """Получение дробного параметра"""
        assert get_float_env_param("FLOAT_PARAM") == 3.14
        assert get_float_env_param("MISSING", default=1.0) == 1.0

        # С запятой вместо точки
        with patch.dict(os.environ, {"FLOAT_PARAM": "3,14"}):
            assert get_float_env_param("FLOAT_PARAM") == 3.14

        # Невалидное значение
        with patch('src.env_settings.utils._env_param_error') as mock_error:
            get_float_env_param("STR_PARAM")
            mock_error.assert_called_with("Float error: STR_PARAM=test_value")

    def test_get_bool_env_param(self):
        """Получение булевого параметра"""
        assert get_bool_env_param("BOOL_PARAM_TRUE") is True
        assert get_bool_env_param("BOOL_PARAM_FALSE") is False
        assert get_bool_env_param("MISSING", default=True) is True

        # Разные варианты True
        for value in ['true', 'yes', 't', 'y', '1']:
            with patch.dict(os.environ, {"BOOL_PARAM": value}):
                assert get_bool_env_param("BOOL_PARAM") is True

        # Разные варианты False
        for value in ['false', 'no', 'n', '0', 'any']:
            with patch.dict(os.environ, {"BOOL_PARAM": value}):
                assert get_bool_env_param("BOOL_PARAM") is False

    def test_get_file_env_param(self, tmp_env):
        """Получение параметра-файла"""
        file_path = tmp_env / "file.txt"
        assert get_file_env_param("FILE_PARAM") == str(file_path)

        # Файл не существует
        with patch('src.env_settings.utils._env_param_error') as mock_error:
            get_file_env_param("STR_PARAM")
            mock_error.assert_called_with(f"File error: STR_PARAM=test_value")

        # Файл не обязателен
        assert get_file_env_param("NEW_PARAM", file_mast_exist=False, dir_mast_exist=False) is None

        # Создание директории для файла
        new_file = tmp_env / "new_dir" / "new_file.txt"
        with patch.dict(os.environ, {"NEW_FILE": str(new_file)}):
            get_file_env_param("NEW_FILE", file_mast_exist=False, dir_mast_exist=True)
            assert new_file.parent.exists()

        # Ошибка создания директории для файла
        config.configure(error_handling=ErrorHandling.PRINT)
        new_file = tmp_env / "fail_dir" / "new_file.txt"
        with patch.dict(os.environ, {"NEW_FILE": str(new_file)}):
            with patch('src.env_settings.utils._create_directory', side_effect=OSError("Permission denied")):
                assert get_file_env_param("NEW_FILE", file_mast_exist=False) is None

    def test_get_filedir_env_param(self, tmp_env):
        """Получение параметра-директории"""
        # Создаем директорию
        dir_path = tmp_env / "test_dir"
        dir_path.mkdir()

        with patch.dict(os.environ, {"DIR_PARAM": str(dir_path)}):
            assert get_filedir_env_param("DIR_PARAM") == str(dir_path)

        # Директория не обязательна
        assert get_filedir_env_param("NEW_DIR", dir_mast_exist=False) is None

        # Создание новой директории
        new_dir = tmp_env / "new_directory"
        with patch.dict(os.environ, {"NEW_DIR": str(new_dir)}):
            get_filedir_env_param("NEW_DIR", dir_mast_exist=True)
            assert new_dir.exists()

        # Ошибка создания директории
        config.configure(error_handling=ErrorHandling.PRINT)
        with patch('src.env_settings.utils._create_directory', side_effect=OSError("Permission denied")) as merr:
            assert get_filedir_env_param("NEW_DIR", dir_mast_exist=True) is None
            merr.assert_called_with(None)


# Тесты для вспомогательных функций
def test_get_value_from_string():
    """Извлечение значения из строки с разделителями"""
    assert get_value_from_string("one;two;three", 2) == "two"
    assert get_value_from_string("one,two,three", 3, separator=',') == "three"
    assert get_value_from_string("single", 1) == "single"
    assert get_value_from_string("", 1) is None
    assert get_value_from_string("a;b;c", 5) is None  # Индекс за пределами


def test_get_values_from_file(tmp_env):
    """Чтение значений из файла"""
    test_file = tmp_env / "values.txt"
    test_file.write_text("line1\nline2\nline3")

    values = get_values_from_file(str(test_file))
    assert values == ["line1", "line2", "line3"]


def test_get_values(tmp_env):
    """Получение значений из разных источников"""
    # Из строки
    assert get_values("a,b,c") == ["a", "b", "c"]

    # Из файла
    # Создаем реальный файл для тестов
    test_file = tmp_env / "file.txt"
    test_file.write_text("file_val1\nfile_val2")
    assert get_values(str(test_file)) == ["file_val1", "file_val2"]

    # Значение по умолчанию
    assert get_values("", default_value="default") == ["default"]
    assert get_values(None, default_value="default") == ["default"]

    # Пустой результат
    assert get_values("") == []
    assert get_values(None) == []


# Тесты для итераторов
def test_endless_param_iterator():
    """Бесконечный итератор параметров"""
    iterator = endless_param_iterator(["a", "b", "c"])
    results = [next(iterator) for _ in range(5)]
    assert results == ["a", "b", "c", "a", "b"]


def test_param_iterator():
    """Конечный итератор параметров"""
    iterator = param_iterator(["a", "b", "c"])
    results = list(iterator)
    assert results == ["a", "b", "c"]


# Тесты для load_env_params
def test_load_env_params(monkeypatch, tmp_env):
    """Тестирование реального поведения загрузки .env файла"""
    import os

    # Временный .env файл для теста
    test_env_content = "TEST_VAR=test_value"
    test_env_file = tmp_env / "test.env"

    with open(test_env_file, "w") as f:
        f.write(test_env_content)

    # Вызываем нашу функцию
    result = load_env_params(str(test_env_file))

    # Проверяем, что переменная загрузилась
    assert os.getenv("TEST_VAR") == "test_value"
    assert result is True  # Предполагая, что load_dotenv вернул True

    # Удаляем временный файл
    os.remove(test_env_file)


# Тест обработки обязательных параметров
def test_required_param_handling(monkeypatch):
    """Проверка обработки обязательных параметров"""
    # Настраиваем стратегию RAISE для удобства тестирования
    config.configure(error_handling=ErrorHandling.RAISE)

    # Для всех типов параметров
    with pytest.raises(ValueError, match="REQUIRED_PARAM"):
        get_str_env_param("REQUIRED_PARAM", required=True)

    with pytest.raises(ValueError, match="REQUIRED_PARAM"):
        get_int_env_param("REQUIRED_PARAM", required=True)

    with pytest.raises(ValueError, match="REQUIRED_PARAM"):
        get_float_env_param("REQUIRED_PARAM", required=True)

    with pytest.raises(ValueError, match="REQUIRED_PARAM"):
        get_bool_env_param("REQUIRED_PARAM", required=True)
