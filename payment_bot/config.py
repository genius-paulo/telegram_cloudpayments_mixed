from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()


class AuthData(BaseModel):
    Authorization: str = Field(description="Authorization data")


class Settings(BaseModel):
    # Креды Telegram
    tg_token: str = os.getenv('API_TOKEN')
    skip_updates: str = True

    # Авторизация для Cloud Payments
    cp_p_id: str = os.getenv('CP_PUBLIC_ID')
    cp_api_pass: str = os.getenv('API_PASSWORD')

    # Креды для бд
    db_name: str = os.getenv('DB_NAME')
    db_user: str = os.getenv('DB_USER')
    db_password: str = os.getenv('DB_PASSWORD')
    db_host: str = os.getenv('DB_HOST')

    # Задержка между проверками платежа и максимальное число попыток
    # Итоговое время ожидания платежа = delay * max_attempts
    delay: int = 3
    max_attempts: int = 100

    # Креды для вебхуков
    webhook_path: str = f"/bot/{tg_token}"
    ngrok_url: str | None = None


settings = Settings()
