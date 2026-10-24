import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

        if not self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL is missing. Set it in your backend .env file "
                "or provide it as an environment variable."
            )


settings = Settings()
