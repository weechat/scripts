# Teknik created by Uncled1023 <admin@teknik.io>
from __future__ import print_function

import_success = True

import sys
import os
import threading
import json
import Tkinter as tk
import tkFileDialog

try:
    import weechat
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: http://www.weechat.org/')
    import_success = False

# Requires Install
try:
    from teknik import uploads as teknik
except ImportError as e:
    print('Missing package(s) for %s: %s' % ('Teknik', e))
    import_success = False

# Weechat Registration
weechat.register("Teknik", "Uncled1023", "1.0.0", "BSD", "Interact with the Teknik Services, including file uploads, pastes, and url shortening.", "script_closed", "")

def upload_file(data):
  try:
    args = json.loads(data)
    if args['file'] is not None and os.path.exists(args['file']):
      # Try to upload the file
      jObj = teknik.UploadFile(args['apiUrl'], args['file'], args['apiUsername'], args['apiToken'])
      return json.dumps(jObj)
  except:
    e = sys.exc_info()[0]
    print("Exception: %s" %e, file=sys.stderr)
  return ''

def process_upload(data, command, return_code, out, err):
  if return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
      weechat.prnt("", "Error with command '%s'" % command)
      return weechat.WEECHAT_RC_OK
  if return_code > 0:
      weechat.prnt("", "return_code = %d" % return_code)
  if out != "":
    results = json.loads(out)
    # Either print the result to the input box, or write the error message to the window
    if 'error' in results:
      weechat.prnt("", 'Error: ' + results['error']['message'])
    elif 'result' in results:      
      buffer = weechat.current_buffer()
      weechat.buffer_set(buffer, 'input', results['result']['url'])
    else:
      weechat.prnt("", 'Unknown Error')
  if err != "":
      weechat.prnt("", "stderr: %s" % err)
  return weechat.WEECHAT_RC_OK

def teknik_set_url(url):
  weechat.config_set_plugin('plugins.var.python.teknik.api_url', url)
  
def teknik_set_token(token):
  weechat.config_set_plugin('plugins.var.python.teknik.token', token)

def teknik_set_username(username):
  weechat.config_set_plugin('plugins.var.python.teknik.username', username)
  
def script_closed():
  # Clean Up Session
  return weechat.WEECHAT_RC_OK
      
def teknik_command(data, buffer, args):
  args = args.strip()
  if args == "":
    weechat.prnt("", "Error: You must specify a command")
  else:
    argv = args.split(" ")
    command = argv[0].lower()
    
    # Upload a File
    if command == 'upload':
      if len(argv) < 2:
        weechat.prnt("", "Error: You must specify a file")
      else:
        # Get current config values
        apiUrl = weechat.config_string(weechat.config_get('plugins.var.python.teknik.api_url'))
        apiUsername = weechat.config_string(weechat.config_get('plugins.var.python.teknik.username'))
        apiToken = weechat.config_string(weechat.config_get('plugins.var.python.teknik.token'))
        
        data = {'file': argv[1], 'apiUrl': apiUrl, 'apiUsername': apiUsername, 'apiToken': apiToken}
        hook = weechat.hook_process('func:upload_file', 0, "process_upload", json.dumps(data))
        
    # Set a config option
    elif command == 'set':
      if len(argv) < 2:
        weechat.prnt("", "Error: You must specify the option to set")
      else:
        option = argv[1].lower()
        if option == 'username':
          if len(argv) < 3:
            weechat.prnt("", "Error: You must specify a username")
          else:
            teknik_set_username(argv[2])
        elif option == 'token':
          if len(argv) < 3:
            weechat.prnt("", "Error: You must specify an auth token")
          else:
            teknik_set_token(argv[2])
        elif option == 'url':
          if len(argv) < 3:
            weechat.prnt("", "Error: You must specify an api url")
          else:
            teknik_set_url(argv[2])
        else:
          weechat.prnt("", "Error: Unrecognized Option")
    else:
      weechat.prnt("", "Error: Unrecognized Command")
  
  return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_success:
  hook = weechat.hook_command("teknik", "Allows uploading of a file to Teknik and sharing the url directly to the chat.",
        "[upload <file>] | [set username|token|url <username|auth_token|api_url>]",
        '          file: The file you want to upload'
        '      username: The username for your Teknik account'
        '    auth_token: The authentication token for your Teknik Account'
        '       api_url: The URL for the Upload API',
        "",
        "teknik_command", "")
