import threading
from pynput import keyboard
import subprocess
from collections import deque

# --- Configuration ---
HOTKEY_SEQUENCE = ['ctrl', 'alt', 'k'] # Represents CTRL + ALT + K
# Convert to a set for faster lookup of pressed keys, but maintain order for sequence
HOTKEY_SEQUENCE_SET = set(HOTKEY_SEQUENCE)
SCRIPT_TO_RUN = ["python", "-m", "src.cli.main"]
# Adjust max_len based on your sequence length and potential for false positives
KEY_PRESS_HISTORY_MAX_LEN = len(HOTKEY_SEQUENCE) * 2

# --- Global Variables ---
# Use a deque for efficient appending and popping from both ends,
# useful for maintaining a history of key presses.
key_press_history = deque(maxlen=KEY_PRESS_HISTORY_MAX_LEN)
current_pressed_keys = set()
script_running_lock = threading.Lock() # To prevent multiple script executions

def on_press(key):
    key_name = None # Initialize key_name

    try:
        # If it's an alphanumeric key, get its character representation
        if hasattr(key, 'char') and key.char is not None:
            key_name = key.char # This will be 'k', 'a', '1', etc. (without quotes)
        else:
            # For special keys (modifiers like ctrl, cmd, alt; or others like esc, enter)
            key_name = str(key).replace("Key.", "") # This will be 'ctrl', 'cmd', 'alt', 'esc', etc.

        if key_name: # Ensure a name was successfully derived
            current_pressed_keys.add(key_name)
            key_press_history.append(key_name)
            print(f"Pressing key: {key_name}")
            check_for_hotkey_sequence()

    except AttributeError:
        # This block might be less necessary with the above 'hasattr(key, 'char')' check,
        # but it's good for robustness if pynput changes how it handles certain keys.
        # It's primarily for keys like Key.esc, Key.f1, etc.
        key_name = str(key).replace("Key.", "")
        if key_name:
            current_pressed_keys.add(key_name)
            key_press_history.append(key_name)
            check_for_hotkey_sequence()
    except Exception as e:
        print(f"Error in on_press: {e}, Key: {key}")

def on_release(key):
    try:
        key_name = str(key).replace("Key.", "")
        if key_name in current_pressed_keys:
            current_pressed_keys.remove(key_name)
        if key == keyboard.Key.esc:
            return False  # Stop listener
    except AttributeError:
        key_name = str(key)
        if key_name in current_pressed_keys:
            current_pressed_keys.remove(key_name)
        if key == keyboard.Key.esc:
            return False # Stop listener

def check_for_hotkey_sequence():
    """
    Checks if the current set of pressed keys matches the hotkey sequence,
    and if the sequence has been pressed in the correct order recently.
    """
    # Check if all required keys for the hotkey are currently pressed
    if not HOTKEY_SEQUENCE_SET.issubset(current_pressed_keys):
        return

    # Check if the sequence appears in the recent history in the correct order
    # We look for the last occurrence of the full sequence.
    # This part needs to be careful about overlapping sequences.
    history_list = list(key_press_history)
    for i in range(len(history_list) - len(HOTKEY_SEQUENCE) + 1):
        if history_list[i : i + len(HOTKEY_SEQUENCE)] == HOTKEY_SEQUENCE:
            print(f"HotKey sequence detected: {HOTKEY_SEQUENCE}")
            execute_script()
            # Clear history after execution to prevent immediate re-triggering
            key_press_history.clear()
            return

def execute_script():
    with script_running_lock:
        print(f"Executing: {' '.join(SCRIPT_TO_RUN)}")
        try:
            # Use Popen for non-blocking execution.
            # You might want to redirect stdout/stderr to a file or /dev/null
            # to avoid console spam if the script is verbose.
            # For example: stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            process = subprocess.Popen(SCRIPT_TO_RUN, cwd='.') # cwd '.' means current directory
            print(f"Script started with PID: {process.pid}")
            # If you want to wait for the script to finish and get its output:
            # output, errors = process.communicate()
            # print(f"Script output:\n{output.decode()}")
            # print(f"Script errors:\n{errors.decode()}")
            # print(f"Script exited with code: {process.returncode}")
        except FileNotFoundError:
            print(f"Error: The command '{SCRIPT_TO_RUN[0]}' was not found. "
                  "Make sure Python is in your PATH and the script path is correct.")
        except Exception as e:
            print(f"An error occurred while executing the script: {e}")

if __name__ == "__main__":
    print(f"Listening for hotkey sequence: {HOTKEY_SEQUENCE}")
    print("Press 'Esc' to exit the listener.")

    # Start the keyboard listener on a separate thread
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    listener.join() # Blocks the main thread until the listener stops
    print("Hotkey listener stopped.")