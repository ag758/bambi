import os
import argparse
from src.core.screenshot_capture import ScreenshotCapture
# from src.core.ocr_processor import OCRProcessor # Removed as it's not used
from src.core.llm_interface import LLMInterface
from src.core.config import AppConfig

def main():
    parser = argparse.ArgumentParser(
        description="Local LLM Assistant for Screenshot Analysis."
    )
    parser.add_argument(
        "query",
        type=str,
        help="Your question about the current screen content."
    )
    # Removed --no-ocr flag as OCR is handled by the VLM inherently
    parser.add_argument(
        "--keep-screenshot",
        action="store_true",
        help="Keep the screenshot file after processing."
    )
    parser.add_argument(
        "--screenshot-path",
        type=str,
        help="Use a pre-existing screenshot file instead of taking a new one."
    )

    args = parser.parse_args()

    # Initialize components
    screenshot_tool = ScreenshotCapture()
    # ocr_processor = OCRProcessor() # No longer needed, as VLM handles text
    llm_interface = LLMInterface()

    screenshot_file = None
    try:
        if args.screenshot_path:
            screenshot_file = args.screenshot_path
            if not os.path.exists(screenshot_file):
                print(f"Error: Provided screenshot file not found at {screenshot_file}")
                return
            print(f"Using pre-existing screenshot: {screenshot_file}")
        else:
            print("Taking screenshot...")
            screenshot_file = screenshot_tool.take_screenshot()
            if not screenshot_file:
                print("Failed to take screenshot. Exiting.")
                return

        # No separate OCR processing step needed here anymore
        # extracted_text = "" # This variable is no longer needed

        print("Sending to LLM for analysis...")
        # Call LLMInterface's get_llm_response with only image_path and user_query
        response = llm_interface.get_llm_response(screenshot_file, args.query)
        print("\n--- LLM Response ---")
        print(response)
        print("--------------------")

    finally:
        if screenshot_file and not args.keep_screenshot and not args.screenshot_path:
            try:
                os.remove(screenshot_file)
                print(f"Cleaned up temporary screenshot: {screenshot_file}")
            except OSError as e:
                print(f"Error cleaning up screenshot {screenshot_file}: {e}")

if __name__ == "__main__":
    main()