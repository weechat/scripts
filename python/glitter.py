import weechat, re

SCRIPT_NAME    = "glitter"
SCRIPT_AUTHOR  = "jotham.read@gmail.com"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Replaces ***text*** you write with rainbow text"

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
   weechat.hook_command_run("/input return", "command_run_input", "")

glitter_pat = re.compile("\*\*\*([^\*]+)\*\*\*")
def glitter_it(match):
   lut = ("13","4","8","9","11","12") # len=6
   text = match.group(1)
   return "".join(["\03"+lut[i%6]+text[i] for i in range(len(text))]) + "\03"

def command_run_input(data, buffer, command):
   if command == "/input return":
      input = weechat.buffer_get_string(buffer, 'input')
      if input.startswith('/set '): # Skip modification of settings
         return weechat.WEECHAT_RC_OK
      input = glitter_pat.sub(glitter_it, input)
      weechat.buffer_set(buffer, 'input', input)
   return weechat.WEECHAT_RC_OK
