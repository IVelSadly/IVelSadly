import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    whatsapp_access_token: str | None = os.getenv("WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str | None = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_verify_token: str | None = os.getenv("WHATSAPP_VERIFY_TOKEN")
    whatsapp_app_secret: str | None = os.getenv("WHATSAPP_APP_SECRET")


settings = Settings()
