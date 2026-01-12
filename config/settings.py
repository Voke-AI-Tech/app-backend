from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # Secrets should come from environment variables (Render dashboard or .env locally)
    GOOGLE_API_KEY: Optional[str] = None
    MODEL: str = "models/gemini-2.5-flash"
    REPLICATE_API_TOKEN: Optional[str] = None
    LAB11_API_KEY: Optional[str] = None

    # Optional Supabase settings (packages present in requirements but not used everywhere)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    # SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    DEVICE: str = "cpu"
    BATCH_SIZE: int = 16
    COMPUTE_TYPE: str = "float16"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def missing_critical(self) -> List[str]:
        """Return a list of critical env vars that are not set.

        This is only informational; callers can use it to log warnings during startup.
        """
        critical = [
            "GOOGLE_API_KEY",
        ]
        missing: List[str] = []
        for name in critical:
            if not getattr(self, name, None):
                missing.append(name)
        return missing
