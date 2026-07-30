from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = ".env", #relative where we are
        env_file_encoding="utf-8",
    )

    database_url: str

    database_url: str = "sqlite+aiosqlite:///./blog.db"

    secret_key : SecretStr
    algorithm: str = 'HS256' #default
    access_token_expire_minutes: int = 30

    max_upload_size_bytes: int = 5 * 1024 * 1024 #5 MB

    posts_per_page: int = 10

    reset_token_expire_minutes: int = 60

    mail_server: str = "localhost"
    mail_port: int = 587 # standart port
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@example.com"
    mail_use_tls: bool = True

    frontend_url: str = "http://localhost:8000" # Bonne pratique contre les attaques

settings = Settings() # Loaded from .env file



