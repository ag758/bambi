import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QTextBrowser)
from PyQt6.QtCore import Qt, QTimer
import markdown # For robust Markdown to HTML conversion if needed

class MarkdownWindow(QMainWindow):
    def __init__(self, title="Markdown Viewer", initial_markdown=""):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 800, 600) # x, y, width, height

        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        self._layout = QVBoxLayout(self._central_widget)

        self._text_browser = QTextBrowser()
        self._text_browser.setOpenExternalLinks(True) # Allow opening links
        self._text_browser.setReadOnly(True) # Ensure it's read-only
        self._layout.addWidget(self._text_browser)

        self.display_markdown(initial_markdown)

        # You can add more widgets here for customization, e.g., a loading indicator
        # self._loading_indicator = QLabel("Loading...")
        # self._loading_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self._loading_indicator.hide() # Initially hidden
        # self._layout.addWidget(self._loading_indicator)

    def display_markdown(self, markdown_text):
        """Displays Markdown text in the window."""
        # QTextBrowser can directly render some Markdown,
        # but for full Markdown spec support, convert to HTML first.
        html_content = markdown.markdown(markdown_text)
        self._text_browser.setHtml(html_content)
        # self._loading_indicator.hide() # Hide loading if shown

    def show_loading(self):
        """Shows a loading indicator (example placeholder)."""
        # self._loading_indicator.show()
        # self._text_browser.clear() # Clear content while loading
        print("Showing loading indicator...") # Placeholder

    def hide_loading(self):
        """Hides the loading indicator."""
        # self._loading_indicator.hide()
        print("Hiding loading indicator...") # Placeholder