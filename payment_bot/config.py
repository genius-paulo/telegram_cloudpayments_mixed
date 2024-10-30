from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()


class AuthData(BaseModel):
    Authorization: str = Field(description="Authorization data")


class Settings(BaseModel):
    # Режим работы бота: polling или webhook
    mode: str = 'polling'  # 'webhook'

    # Креды Telegram
    tg_token: str = os.getenv('API_TOKEN')
    skip_updates: str = True
    webhook_path: str = f"/bot/{tg_token}"
    ngrok_url: str | None = 'https://dd6e-95-25-249-191.ngrok-free.app'

    # Авторизация для Cloud Payments
    cp_p_id: str = os.getenv('CP_PUBLIC_ID')
    cp_api_pass: str = os.getenv('API_PASSWORD')

    # Задержка между проверками платежа и максимальное число попыток
    # Итоговое время ожидания платежа = delay * max_attempts
    delay: int = 3
    max_attempts: int = 100


settings = Settings()

