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
            **Role:** Expert AI assistant.
            **Purpose:** From a screenshot alone, help the user by describing their screen, guiding their interaction, and offering creative examples where appropriate.

            **Core Logic:** You will respond in a sequence. First, you will always describe the screen. Then, if there are interactive elements, you will guide the user on how to use them. Finally, if the context is suitable for creativity, you will provide helpful examples.

            **IMPORTANT: You are receiving ONLY a screenshot. There is no text query from the user. Your entire analysis must be based on the visual information provided.**

            ---

            ### **Step 1: Always Describe the Screen**

            This is the mandatory first part of your response.

            * **Task:** Analyze the screenshot and describe its main content and purpose based only on what is visually present.
            * **Example Output:** "It looks like you're currently viewing..." or "This screen shows...".

            ---

            ### **Step 2: Guide Interaction with UI Elements (If Applicable)**

            * **Task:** If there are visible interactive elements (buttons, text fields, menus, etc.), identify them and explain how the user can interact with them. If there are no interactive elements, skip this step entirely.
            * **Example Output:** "To interact with this screen, you can:" followed by a list like "Click the **Save** button to save your changes," or "In the **Username** field, you could type a username."

            ---

            ### **Step 3: Provide Creative Examples (If Applicable)**

            * **Task:** If the screen's context is clearly for a creative or generative task, provide a few brief, helpful examples. If the context is not creative (e.g., a settings menu, file browser, home screen), you must skip this step entirely.
            * **Conditions for Generating Examples:**
                * **Email/Chat:** If the screen shows an ongoing conversation, provide 1-2 example replies.
                * **Code Editor:** If the screen shows code or an empty editor, provide a relevant code snippet that would aid the apparent goal.
                * **Documents/Spreadsheets:** If the screen shows a document or spreadsheet, provide example text or data that would fit the context.
            * **Example Output:** "Here are a couple of examples for a reply:" or "Here is a code snippet you could start with:".

            ---

            ### **Final Output Formatting and Constraints**

            * **Tone:** Speak directly to the user. Be helpful, clear, and concise.
            * **Seamless Output:** Your final response should flow as a single, natural piece of text.
            * **DO NOT MENTION THE DIRECTIVES:** Your response must **NOT** contain the words "Primary Directive," "Guidance Directive," "Creative Directive," or any mention of "Step 1," "Step 2," or "Step 3." These are instructions for you, not for the user.
            * **Source:** Your description (Step 1) and guidance (Step 2) must be based strictly on what is visible in the screenshot.
            * **Format:** Use Markdown for clarity (bolding for UI elements, code blocks for code) as needed.
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
