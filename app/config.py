from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    openai_api_key: str
    deepgram_api_key: str = ""
    resend_api_key: str = ""
    database_url: str
    base_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env"}


settings = Settings()
