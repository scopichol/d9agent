import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Завантажуємо змінні середовища з .env файлу
load_dotenv()

class Settings(BaseSettings):
    # Ключ API для OpenAI (обов’язково треба вказати у .env)
    openai_api_key: str
    
    # Налаштування хоста і порту для FastAPI
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    
    # Порт для Streamlit UI
    streamlit_port: int = 8503

    class Config:
        # Файл, де зберігаються змінні середовища
        env_file = ".env"
        env_file_encoding = "utf-8"

# Створюємо єдиний об’єкт налаштувань, який імпортуємо по всьому проєкту
settings = Settings() # type: ignore