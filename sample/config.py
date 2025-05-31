import os
from dotenv import load_dotenv
from errors import ConfigError

load_dotenv(verbose=True)

class Config:
    def get(self, key: str) -> str:
        val = os.getenv(key)
        if val is None:
            raise ConfigError(f"Not found: {key}")
        return val
