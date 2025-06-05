import requests
import base64
import os
from src.core.config import AppConfig
from PIL import Image # Import Pillow
import io

class LLMInterface:
    def __init__(self, host=AppConfig.OLLAMA_HOST, model=AppConfig.OLLAMA_MODEL):
        self.host = host
        self.model = model
        self.api_url = AppConfig.get_ollama_api_url("generate")
        self.pull_url = AppConfig.get_ollama_api_url("pull")
        self.tags_url = AppConfig.get_ollama_api_url("tags")
        self.max_image_dim = 1000
        
    def _resize_image(self, image_path, max_dim):
        """
        Resizes an image to have its longest side no more than `max_dim`,
        maintaining aspect ratio, and returns it as bytes.
        Handles RGBA to RGB conversion for JPEG saving.
        """
        try:
            img = Image.open(image_path)
            original_width, original_height = img.size
            print(f"Original image resolution: {original_width}x{original_height}")

            # --- NEW: Convert to RGB if the image is RGBA ---
            if img.mode == 'RGBA':
                # Create a new blank RGB image with a white background
                # and paste the RGBA image onto it.
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3]) # Use the alpha channel as a mask
                img = background
                print("Converted RGBA image to RGB for JPEG saving.")
            # --- END NEW ---

            if max(original_width, original_height) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                print(f"Resized image resolution: {img.width}x{img.height}")
            else:
                print("Image resolution is already within limits, no resizing needed.")

            # Convert image to bytes in JPEG format for Ollama
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG") # This line will now work correctly for RGB images
            return buffered.getvalue()
        except Exception as e:
            print(f"Error resizing image: {e}")
            # Fallback: if resize fails, try to return original image bytes
            # Note: This fallback might still fail if the original image is RGBA and you try to base64 encode it for an API expecting JPEG/PNG
            try:
                with open(image_path, "rb") as f:
                    return f.read()
            except Exception as read_error:
                print(f"Also failed to read original image bytes: {read_error}")
                return None # Or raise an error, depending on desired behavior

    def get_llm_response(self, image_path, user_query):

        if not user_query:
            user_query = """
            You are an expert AI assistant whose purpose is to help the user understand their current screen and guide them on their task.

            Based *STRICTLY* on **ONLY** the visible text and visual information in this image:
            Do NOT invent or infer any details not directly shown. If a piece of requested information is not visible or not relevant to the screen's main purpose, explicitly state 'Not applicable/Not visible'.

            1.  Speak directly to the user (e.g., "It looks like you are currently viewing a product page," or "It appears you are setting up a new account"). Clearly state what the main goal or context of the screen is.
            2.  * Identify the main context or purpose of the screen (e.g., "Invoice viewing page," "Software installation wizard," "Shopping cart").
                * Extract all prominent textual labels, numerical data, and important phrases relevant to the screen's purpose.
                * List any identified interactive elements (buttons, links, input fields, dropdowns, checkboxes, etc.) and their visible text.
            3.  If there are visible empty input areas or fields requiring user entry, suggest examples of input that would fit based on their labels or context.
            4.  Suggest next steps for the user to make progress in the main context or purpose. These steps must be directly inferable from the visible UI elements (e.g., clicking a specific button, typing into a field, selecting an option). 
            Guide the user on how to progress with the task depicted on the screen.

            Ensure your entire response is clear, concise, highly actionable, and speaks directly to the user.
            """

        """
        Sends the screenshot (as base64) and user query to the local multimodal LLM.
        The LLM is expected to perform the OCR-like understanding internally.
        """

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at: {image_path}")

        # Resize the image and get its bytes
        image_bytes = self._resize_image(image_path, self.max_image_dim)
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')

        # The prompt is now simpler, as the LLM directly interprets the image
        # You can prompt it more generally or ask it to describe visible text.
        prompt = f"USER: <image>\nBased on this screen, '{user_query}'\nASSISTANT:"

        print("\nModel: ", self.model)
        print("\nPrompt: ", prompt)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [encoded_image],
            "stream": False
        }

        headers = {'Content-Type': 'application/json'}

        try:
            print("\nAPI URL: ", self.api_url)
            print("\nAPI Headers: ", headers)
            # print("\nPayload: ", payload)
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
