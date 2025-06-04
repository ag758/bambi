import mss
import mss.tools
import os
from PIL import Image
import time
from datetime import datetime
from src.core.config import AppConfig

class ScreenshotCapture:
    def __init__(self, output_dir=AppConfig.TEMP_SCREENSHOT_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True) # Ensure dir exists

    def take_screenshot(self, filename=None):
        """
        Takes a screenshot of the primary monitor and saves it to a file.
        Returns the path to the saved screenshot.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        filepath = os.path.join(self.output_dir, filename)

        with mss.mss() as sct:
            # Get information of monitor 1 (primary monitor)
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            # Convert to PIL Image for easier processing
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            img.save(filepath)

        print(f"Screenshot saved to: {filepath}")
        return filepath

# Example usage (for testing)
if __name__ == "__main__":
    screenshot_tool = ScreenshotCapture()
    path = screenshot_tool.take_screenshot()
    print(f"Screenshot taken: {path}")