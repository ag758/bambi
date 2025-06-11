import threading
from pynput import keyboard
import subprocess # subprocess is imported but not used in the provided snippet. If needed, ensure its usage.
from collections import deque

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QTextBrowser, QLabel) # Added QLabel
from PyQt6.QtCore import QObject, pyqtSignal, QMetaObject, Qt, QTimer
import sys
import markdown # For robust Markdown to HTML conversion if needed

class MarkdownWindow(QMainWindow):
    def __init__(self, title="Markdown Viewer", initial_markdown=""):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 800, 600) # x, y, width, height

        # --- Window Styling for Chat-like Appearance ---
        # Set a subtle background for the main window
        self.setStyleSheet("QMainWindow { background-color: #f0f2f5; }") # Light gray/blue

        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        # Add padding to the central widget to create space around the text browser
        self._central_widget.setStyleSheet("QWidget { padding: 10px; }")
        self._layout = QVBoxLayout(self._central_widget)
        self._layout.setContentsMargins(0, 0, 0, 0) # Remove default layout margins
        self._layout.setSpacing(10) # Spacing between widgets


        self._text_browser = QTextBrowser()
        self._text_browser.setOpenExternalLinks(True) # Allow opening links
        self._text_browser.setReadOnly(True) # Ensure it's read-only
        # --- QTextBrowser Styling for Chat-like Bubble ---
        self._text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff; /* White background for the chat area */
                border: 1px solid #e0e0e0; /* Light gray border */
                border-radius: 15px; /* Rounded corners */
                padding: 15px; /* Inner padding for text */
                font-weight: bold;
                font-size: 14px;
                color: #555555; /* Darker gray for readability */
            }
        """)
        self._layout.addWidget(self._text_browser)

        # Initialize the loading indicator
        self._loading_label = QLabel("Bambi is thinking") # More descriptive initial text
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center the text
        # --- Loading Indicator Styling ---
        self._loading_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #555555; /* Darker gray for readability */
                font-weight: bold;
                padding: 10px;
                border-radius: 10px;
                background-color: #e6e9ed; /* Subtle background for the typing indicator */
            }
        """)
        self._loading_label.hide() # Initially hidden
        self._layout.addWidget(self._loading_label)

        # --- Loading Animation Timer ---
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(400) # Update every 400ms
        self._animation_step = 0
        self._animation_text_base = "Bambi is thinking"
        # Connect the timer timeout signal to the animation update slot
        self._animation_timer.timeout.connect(self._update_loading_animation)

        self.display_markdown(initial_markdown)

    def _update_loading_animation(self):
        """Updates the text of the loading label to create a typing animation."""
        dots = "." * (self._animation_step % 4) # Cycle between 0, 1, 2, 3 dots
        self._loading_label.setText(f"{self._animation_text_base}{dots}")
        self._animation_step += 1

    def display_markdown(self, markdown_text):
        """Displays Markdown text in the window and hides the loading indicator."""
        # Stop the animation timer
        self._animation_timer.stop()
        # Ensure the text browser is visible and loading label is hidden
        self._text_browser.show()
        self._loading_label.hide()

        # QTextBrowser can directly render some Markdown,
        # but for full Markdown spec support, convert to HTML first.
        html_content = markdown.markdown(markdown_text)
        self._text_browser.setHtml(html_content)


    def show_loading(self, message_base="Bambi is thinking"):
        """Shows a loading indicator and hides the text browser. Starts the animation."""
        self._text_browser.hide() # Hide the text browser
        self._animation_text_base = message_base
        self._animation_step = 0 # Reset animation step
        self._update_loading_animation() # Set initial text
        self._loading_label.show() # Show the loading label
        self._animation_timer.start() # Start the animation timer
        print(f"Showing loading indicator with message base: '{message_base}'")


    def hide_loading(self):
        """Hides the loading indicator and shows the text browser. Stops the animation."""
        self._animation_timer.stop() # Stop the animation timer
        self._loading_label.hide()
        self._text_browser.show() # Show the text browser again
        print("Hiding loading indicator.")


if __name__ == "__main__":
    # --- Main Application Setup ---
    # 1. Create the QApplication instance FIRST on the main thread.
    app = QApplication(sys.argv)

    # 2. Instantiate your LLMAssistant and MarkdownWin