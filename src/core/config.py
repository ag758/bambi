import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class AppConfig:
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llava:7b-v1.5-q4_K_M") # Default VLM
    TEMP_SCREENSHOT_DIR = os.getenv("TEMP_SCREENSHOT_DIR", "data/temp/")
    # Add other configurations as needed (e.g., OCR language, image quality)

    @classmethod
    def get_ollama_api_url(cls, endpoint="generate"):
        return f"{cls.OLLAMA_HOST}/api/{endpoint}"

# Ensure temp directory exists
os.makedirs(AppConfig.TEMP_SCREENSHOT_DIR, exist_ok=True)