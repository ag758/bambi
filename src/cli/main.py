import os
import argparse
from src.core.screenshot_capture import ScreenshotCapture
from src.core.llm_interface import LLMInterface
from src.core.config import AppConfig # Assuming this is still used for configuration, though not explicitly in the main logic shown

class LLMAssistant:
    def __init__(self):
        """
        Initializes the LLMAssistant with necessary tools.
        """
        self.screenshot_tool = ScreenshotCapture()
        self.llm_interface = LLMInterface()

    def analyze_screen(self, query: str = None, keep_screenshot: bool = False, screenshot_path: str = None) -> str | None:
        """
        Captures a screenshot, analyzes it with an LLM, and returns the response.

        Args:
            query (str, optional): Your question about the current screen content. Defaults to None.
            keep_screenshot (bool, optional): Whether to keep the screenshot file after processing. Defaults to False.
            screenshot_path (str, optional): Path to a pre-existing screenshot file. If provided, a new screenshot won't be taken. Defaults to None.

        Returns:
            str | None: The LLM's response as a string, or None if an error occurred.
        """
        screenshot_file = None
        response = None
        try:
            if screenshot_path:
                screenshot_file = screenshot_path
                if not os.path.exists(screenshot_file):
                    print(f"Error: Provided screenshot file not found at {screenshot_file}")
                    return None
                print(f"Using pre-existing screenshot: {screenshot_file}")
            else:
                print("Taking screenshot...")
                screenshot_file = self.screenshot_tool.take_screenshot()
                if not screenshot_file:
                    print("Failed to take screenshot. Exiting.")
                    return None

            print("Sending to LLM for analysis...")
            response = self.llm_interface.get_llm_response(screenshot_file, query)
            print("\n--- LLM Response ---")
            print(response)
            print("--------------------")

            return response

        finally:
            if screenshot_file and not keep_screenshot and not screenshot_path:
                try:
                    os.remove(screenshot_file)
                    print(f"Cleaned up temporary screenshot: {screenshot_file}")
                except OSError as e:
                    print(f"Error cleaning up screenshot {screenshot_file}: {e}")