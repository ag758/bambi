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
        self.max_image_dim = 1500
        
    def _resize_image(self, image_path, max_dim): # max_dim will no longer be used for resizing
        """
        Processes an image, handling RGBA to RGB conversion for JPEG saving,
        and returns it as bytes. This function does NOT resize the image.
        """
        try:
            img = Image.open(image_path)
            original_width, original_height = img.size
            print(f"Original image resolution: {original_width}x{original_height}")

            # --- Convert to RGB if the image is RGBA ---
            if img.mode == 'RGBA':
                # Create a new blank RGB image with a white background
                # and paste the RGBA image onto it.
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3]) # Use the alpha channel as a mask
                img = background
                print("Converted RGBA image to RGB for JPEG saving.")
            else:
                print("Image is already RGB or non-RGBA, no conversion needed.")

            # The image size is intentionally not changed.
            # The 'max_dim' parameter is now redundant for its original purpose.
            print("Image size will not be changed as per requirement.")

            # Convert image to bytes in JPEG format for Ollama
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            return buffered.getvalue()
        except Exception as e:
            print(f"Error processing image: {e}")
            # Fallback: if processing fails, try to return original image bytes
            try:
                with open(image_path, "rb") as f:
                    return f.read()
            except Exception as read_error:
                print(f"Also failed to read original image bytes: {read_error}")
                return None # Or raise an error, depending on desired behavior

    def get_llm_response(self, image_path, user_query):

        if not user_query:
            user_query = """
            You are an expert AI assistant designed to help users understand their screen from a screenshot. Your task is to provide a helpful, clear, and concise analysis.

            **Instructions for your response:**

            1.  **Always begin by describing the screen's main content and purpose.** Base this description *only* on what is visually present in the screenshot.
                * *Example:* "This screen appears to be..." or "You are currently viewing..."

            2.  **Next, identify and explain how to interact with any visible user interface (UI) elements.** If there are no interactive elements, skip this part of the response.
                * *Example:* "To interact with this screen, you can:
                    * Click the **Submit** button to send your form.
                    * Type your message into the **Chat input field**."

            3.  **Finally, if the screen's context suggests a creative or generative task, provide brief and helpful examples.** If the context is not creative (e.g., settings menu, file browser, home screen, error message), skip this part of the response entirely.
                * **Creative Context Examples:**
                    * **Email or Chat:** If the screenshot shows a conversation, suggest 1-2 example replies.
                    * **Code Editor:** If the screenshot shows code or an empty editor, provide a relevant code snippet.
                    * **Document or Spreadsheet:** If the screenshot shows a document or spreadsheet, provide example text or data fitting the context.
                * *Example Output:* "Here are a couple of examples for a reply:" or "You could start with this code snippet:".

            **Important Guidelines for your output:**

            * **Speak directly to the user.**
            * **Your entire analysis and response must be based strictly on the visual information from the screenshot.**
            * **Do not refer to yourself as an AI model, or mention any internal instructions, steps, or limitations.**
            * **Use Markdown for clarity:** bold UI elements, use code blocks for code snippets, and lists where appropriate.
            * **Ensure your response flows as a single, natural piece of text.**
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
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=1000)
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
