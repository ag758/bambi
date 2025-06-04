import requests
import base64
import os
from src.core.config import AppConfig
import json # Ensure json is imported for parsing Ollama stream

class LLMInterface:
    def __init__(self, host=AppConfig.OLLAMA_HOST, model=AppConfig.OLLAMA_MODEL):
        self.host = host
        self.model = model
        self.api_url = AppConfig.get_ollama_api_url("generate")
        self.pull_url = AppConfig.get_ollama_api_url("pull")
        self.tags_url = AppConfig.get_ollama_api_url("tags")

    def _check_ollama_status(self):
        try:
            response = requests.get(self.tags_url, timeout=5)
            response.raise_for_status()
            return True
        except requests.exceptions.ConnectionError:
            return False
        except Exception as e:
            print(f"Error checking Ollama status: {e}")
            return False

    def _pull_model(self):
        print(f"Attempting to download model: {self.model}. This may take a while...")
        headers = {'Content-Type': 'application/json'}
        data = {"name": self.model, "stream": True}
        try:
            with requests.post(self.pull_url, headers=headers, json=data, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=None):
                    for line in chunk.decode('utf-8').splitlines():
                        if line.strip():
                            try:
                                progress = json.loads(line)
                                if 'total' in progress and 'completed' in progress:
                                    percent = progress['completed'] / progress['total']
                                    print(f"\rDownloading {self.model}: {percent:.2%}", end="", flush=True)
                                elif 'status' in progress:
                                    print(f"\rStatus: {progress['status']}", end="", flush=True)
                            except json.JSONDecodeError:
                                # Sometimes status messages aren't perfect JSON, or lines are incomplete
                                continue
            print(f"\nModel {self.model} downloaded successfully.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"\nFailed to download {self.model}: {e}")
            return False

    def get_llm_response(self, image_path, user_query):
        """
        Sends the screenshot (as base64) and user query to the local multimodal LLM.
        The LLM is expected to perform the OCR-like understanding internally.
        """
        if not self._check_ollama_status():
            print("Ollama server is not running. Please start Ollama or install it from ollama.com/download")
            if not self._pull_model():
                return "Failed to get LLM model. Please check your Ollama installation and network."
            else:
                # After successful pull, check status again to confirm model is ready
                # This might not be strictly necessary if pull was successful, but adds robustness
                if not self._check_ollama_status():
                    return "Ollama started, but model still not available. Try again or check Ollama logs."
                print("Ollama is now running and model should be ready.")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at: {image_path}")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # The prompt is now simpler, as the LLM directly interprets the image
        # You can prompt it more generally or ask it to describe visible text.
        prompt = f"USER: <image>\nBased on this screen, '{user_query}'\nASSISTANT:"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_data],
            "stream": False
        }

        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "No response from LLM.")
        except requests.exceptions.ConnectionError:
            return "Could not connect to Ollama server. Make sure it's running."
        except requests.exceptions.Timeout:
            return "Ollama server timed out. Model inference might be slow."
        except requests.exceptions.RequestException as e:
            return f"Error communicating with Ollama: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

# Example usage (for testing)
if __name__ == "__main__":
    from src.core.screenshot_capture import ScreenshotCapture
    import os

    screenshot_tool = ScreenshotCapture()
    test_screenshot_path = screenshot_tool.take_screenshot(filename="llm_test_screenshot_no_ocr.png")

    llm_tool = LLMInterface()
    user_q = "What is the primary content on this screen and what can I do with it? Describe any visible text."
    print(f"\nAsking LLM: '{user_q}'")
    # Corrected call: only image_path and user_query
    llm_response = llm_tool.get_llm_response(test_screenshot_path, user_q)
    print("\nLLM Response:\n", llm_response)

    if os.path.exists(test_screenshot_path):
        os.remove(test_screenshot_path)