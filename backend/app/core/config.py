from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    DATABASE_URL: str = "postgresql+asyncpg://ctdp:devpassword@localhost:5432/chip_test_db"
    RABBITMQ_URL: str = "amqp://ctdp:devpassword@localhost:5672/chip_test"
    REDIS_URL: str = "redis://localhost:6379/0"
    STORAGE_PATH: str = "./storage"

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24시간

    FAIL_RATE_THRESHOLD: float = 0.10  # Redis Pub/Sub 이벤트 임계치


settings = Settings()
