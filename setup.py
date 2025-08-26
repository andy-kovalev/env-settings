from setuptools import setup, find_packages

setup(
    name="env-settings",                    # Имя для pip install
    version="0.0.1",                        # Версия
    author="Andy Kovalev",
    description="Universal module for using Python program settings based on environment variables",
    package_dir={"": "src"},                # Где искать пакеты
    packages=find_packages(where="src"),    # Автопоиск пакетов в src
    python_requires=">=3.6",                # Совместимость
    install_requires=['python-dotenv'],     # Зависимости
    extras_require={}                       # Доп. зависимости
)
