from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration comes from environment variables (see .env.example).
    Never hard-code secrets or credentials here.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./test.db"
    jwt_secret: str = "testsecret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cookie_secure: bool = False

    storage_provider: str = "local"
    storage_local_path: str = "./storage"
    storage_bucket: str = "zeramai-hr-documents"

    company_name: str = "Zeramai Technologies Pvt Ltd"


settings = Settings()
