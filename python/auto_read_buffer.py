# -*- coding: utf-8 -*-
import weechat

SCRIPT_NAME = "auto_read_buffer"
SCRIPT_AUTHOR = "Stef Dunlap <hello@kindrobot.ca>"
SCRIPT_VERSION = "1.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Automatically marks a buffer as read upon switching away"

# Global variable to store the current buffer
current_buffer = None

# Callback for the buffer switch signal
def buffer_switch_cb(data, signal, signal_data):
    global current_buffer
    # If there is a previously focused buffer, mark it as read
    if current_buffer is not None:
        weechat.buffer_set(current_buffer, "hotlist", "-1")
    # Update current_buffer to the new buffer
    current_buffer = signal_data
    return weechat.WEECHAT_RC_OK

# Callback to update current_buffer when script loads
def buffer_opened_cb(data, signal, signal_data):
    global current_buffer
    current_buffer = signal_data
    return weechat.WEECHAT_RC_OK

if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        # Hook into the buffer switch and buffer opened signals
        weechat.hook_signal("buffer_switch", "buffer_switch_cb", "")
        weechat.hook_signal("buffer_opened", "buffer_opened_cb", "")