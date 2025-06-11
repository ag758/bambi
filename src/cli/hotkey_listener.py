import threading
from pynput import keyboard
import subprocess # subprocess is imported but not used in the provided snippet. If needed, ensure its usage.
from collections import deque

# Assuming these are available from your project structure
from src.cli.main import LLMAssistant
from src.cli.markdown_window import MarkdownWindow

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QTextBrowser, QLabel) # Added QLabel
from PyQt6.QtCore import QObject, pyqtSignal, QMetaObject, Qt
import sys
import markdown # For robust Markdown to HTML conversion if needed


# --- Configuration ---
# Represents CTRL + ALT + K. Ensure these match pynput's string representation.
HOTKEY_SEQUENCE = ['ctrl', 'alt', 'k']
# Convert to a set for faster lookup of pressed keys, but maintain order for sequence
HOTKEY_SEQUENCE_SET = set(HOTKEY_SEQUENCE)
# Adjust max_len based on your sequence length and potential for false positives
KEY_PRESS_HISTORY_MAX_LEN = len(HOTKEY_SEQUENCE) * 2

# --- Global Variables ---
# Use a deque for efficient appending and popping from both ends,
# useful for maintaining a history of key presses.
key_press_history = deque(maxlen=KEY_PRESS_HISTORY_MAX_LEN)
current_pressed_keys = set()
script_running_lock = threading.Lock() # To prevent multiple script executions

class HotKeyListener(QObject): # Inherit from QObject to enable Qt signals

    # Define a custom signal to update the Markdown window from the listener thread.
    hotkey_triggered = pyqtSignal()
    # New signal to send the analysis result back to the main thread
    analysis_complete = pyqtSignal(str) # Signal to carry the response string

    def __init__(self, assistant_instance, markdown_viewer_instance):
        """
        Initializes the HotKeyListener.

        Args:
            assistant_instance: An instance of LLMAssistant.
            markdown_viewer_instance: An instance of MarkdownWindow.
        """
        super().__init__()
        self.assistant = assistant_instance
        self.markdown_viewer = markdown_viewer_instance

        # Connect the custom hotkey signal to the main script execution slot
        self.hotkey_triggered.connect(self._execute_script_on_main_thread)
        # Connect the analysis complete signal to the slot that updates the UI
        self.analysis_complete.connect(self._display_response_and_hide_loading)


    def on_press(self, key):
        """
        Callback function for when a key is pressed.
        Adds the key to current_pressed_keys and key_press_history, then checks for hotkey.
        """
        key_name = None

        try:
            # Handle character keys (like 'a', 'b', '1')
            if hasattr(key, 'char') and key.char is not None:
                key_name = key.char
            # Handle special keys (like 'ctrl', 'alt', 'esc')
            else:
                key_name = str(key).replace("Key.", "")

            if key_name: # Ensure a valid key name was obtained
                current_pressed_keys.add(key_name)
                key_press_history.append(key_name)
                # print(f"Pressed: {key_name}, Current: {current_pressed_keys}, History: {list(key_press_history)}")
                self.check_for_hotkey_sequence()

        except Exception as e:
            # Catch any unexpected errors during key processing
            print(f"Error in on_press for key {key}: {e}")

    def on_release(self, key):
        """
        Callback function for when a key is released.
        Removes the key from current_pressed_keys. Stops the listener if 'Esc' is released.
        """
        try:
            key_name = str(key).replace("Key.", "")
            if key_name in current_pressed_keys:
                current_pressed_keys.remove(key_name)
            # print(f"Released: {key_name}, Current: {current_pressed_keys}")
            if key == keyboard.Key.esc:
                print("Escape key released. Stopping listener.")
                return False  # Return False to stop the pynput listener

        except Exception as e:
            print(f"Error in on_release for key {key}: {e}")


    def check_for_hotkey_sequence(self):
        """
        Checks if the current set of pressed keys matches the hotkey sequence,
        and if the sequence has been pressed in the correct order recently.
        """
        # First, quickly check if all required hotkey modifier/character keys are currently held down.
        if not HOTKEY_SEQUENCE_SET.issubset(current_pressed_keys):
            return

        # Then, check if the specific sequence appeared in the history in the correct order.
        history_list = list(key_press_history)
        # Iterate backwards through history_list to find the most recent match efficiently.
        for i in range(len(history_list) - len(HOTKEY_SEQUENCE) + 1):
            if history_list[i : i + len(HOTKEY_SEQUENCE)] == HOTKEY_SEQUENCE:
                print(f"Hotkey sequence detected: {HOTKEY_SEQUENCE}")
                # Emit the signal to trigger the script execution on the main thread.
                self.hotkey_triggered.emit()
                # Clear history after execution to prevent immediate re-triggering
                # and to avoid multiple triggers for a single long press.
                key_press_history.clear()
                return

    def _execute_script_on_main_thread(self):
        """
        This method is a slot connected to hotkey_triggered signal.
        It runs on the main GUI thread and safely prepares the UI for analysis.
        """
        # Use a lock to ensure only one script execution runs at a time.
        if not script_running_lock.acquire(blocking=False):
            print("Script already running, ignoring hotkey.")
            return

        try:
            print("Hotkey script triggered. Preparing UI for analysis...")
            # Bring the window to the front and activate it
            self.markdown_viewer.showNormal() # Restore from minimized state if applicable
            self.markdown_viewer.activateWindow() # Bring to front and give focus
            self.markdown_viewer.raise_() # Ensure it's stacked on top of other windows

            self.markdown_viewer.show() # Show the window
            self.markdown_viewer.show_loading() # Show the loading indicator

            # Force the GUI to process events (like window show/paint events)
            QApplication.processEvents()

            # Start the potentially long-running analyze_screen in a new thread
            analysis_thread = threading.Thread(target=self._run_analysis_in_background, daemon=True)
            analysis_thread.start()

        except Exception as e:
            print(f"An error occurred while preparing script execution: {e}")
            self.markdown_viewer.hide_loading() # Ensure loading is hidden even on error
            script_running_lock.release() # Release lock on error

    def _run_analysis_in_background(self):
        """
        This method runs in a separate thread to perform the screen analysis.
        It emits a signal upon completion.
        """
        try:
            print("Starting screen analysis in background thread...")
            response = self.assistant.analyze_screen()
            print("Screen analysis complete in background thread.")
            # Emit the signal with the response, which will be handled on the main thread
            self.analysis_complete.emit(response)
        except Exception as e:
            print(f"An error occurred during background analysis: {e}")
            # Consider emitting an error signal here if you need to handle errors in UI
            self.analysis_complete.emit(f"Error: {e}") # Send error message to UI
        finally:
            script_running_lock.release() # Ensure the lock is always released

    def _display_response_and_hide_loading(self, response):
        """
        This slot receives the analysis result from the background thread
        and updates the UI on the main thread.
        """
        print("Displaying response and hiding loading indicator.")
        self.markdown_viewer.display_markdown(response) # Display the markdown content
        self.markdown_viewer.hide_loading() # Hide the loading indicator

    def run_listener_thread(self):
        """
        Starts the pynput keyboard listener in a separate thread.
        This method is designed to be the target for a threading.Thread.
        """
        print(f"Starting hotkey listener thread. Listening for: {HOTKEY_SEQUENCE}")
        print("Press 'Esc' to exit the listener.")

        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start() # Start the listener thread
        listener.join()  # Block this thread until the listener stops (e.g., by 'Esc')
        print("Hotkey listener thread stopped.")


if __name__ == "__main__":
    # --- Main Application Setup ---
    # 1. Create the QApplication instance FIRST on the main thread.
    app = QApplication(sys.argv)

    # 2. Instantiate your LLMAssistant and MarkdownWindow.
    # These will be managed by the QApplication's event loop.
    assistant_instance = LLMAssistant()
    markdown_viewer_instance = MarkdownWindow(title="Bambi")

    # 3. Create the HotKeyListener instance, passing it references to the assistant
    # and markdown viewer so it can interact with them safely via signals.
    hotkey_listener_obj = HotKeyListener(assistant_instance, markdown_viewer_instance)

    # 4. Start the pynput keyboard listener in a separate Python thread.
    # Set daemon=True so the thread automatically exits when the main application exits.
    listener_thread = threading.Thread(target=hotkey_listener_obj.run_listener_thread, daemon=True)
    listener_thread.start()

    # 5. Start the PyQt application's event loop on the main thread.
    # This keeps the GUI responsive and processes all Qt events and signals.
    # The application will exit when the last window is closed or app.quit() is called.
    sys.exit(app.exec())

