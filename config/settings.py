from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    GOOGLE_API_KEY: str = "AIzaSyAyjyZmom_RrhRcFvW8GTFDaewcUcgDR_o"
    MODEL: str = "models/gemini-2.5-flash"
    REPLICATE_API_TOKEN: str = "r8_YdRzqhcKXwPsfnrexFE67KJBeWDTy1S1r09NE"
    LAB11_API_KEY: str = "sk_9077fb4ba0f5347b6c82eaccba4802152f2ba25bac50a421"
    DEVICE: str = "cpu"
    BATCH_SIZE: int = 16
    COMPUTE_TYPE: str = "float16"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
