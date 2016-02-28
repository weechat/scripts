# ===============================================================
# weeechat-axolotl.py (c) 2014-2016 by David R. Andersen <k0rx@rxcomm.net>
# based on:
# crypt.py (c) 2008-2012 by Nicolai Lissner <nlissne@linux01.org>
# ===============================================================
SCRIPT_NAME    = "axolotl"
SCRIPT_AUTHOR  = "David R. Andersen <k0rx@rxcomm.net>"
SCRIPT_VERSION = "0.1.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "encrypt/decrypt PRIVMSGs using axolotl ratchet and GPG"

"""
This plugin uses the Axolotl ratchet protocol with
gnupg to encrypt/decrypt messages you send or
receive with weechat. The script is largely copied
from the weechat crypt.py script. Thanks to the authors
for that! The script requires the Axolotl python module.
This module is available at:
https://github.com/rxcomm/pyaxo

you can add 'axolotl' to  weechat.bar.status.items to
have an indication that the message you are going to send
is encrypted (i.e. a database exists).

Example usage: if your nick is thingone, and the nick you want
to pm privately with is thingtwo, you would
generate two database files thingone.db and thingtwo.db
using the gen_weechat_database_pair.py utility.
thingtwo.db would go in your weechat directory, and
thingone.db would go in thingtwo's weechat directory.

If your buddy wants to re-encrypt his database with a
different password, he can do that directly with gpg.

 echo <oldpassword> | gpg --passphrase-fd=0 -d thingone.db | gpg --output thingone.db --cipher-algo AES256 -c

For some reason gpg won't prompt for the new passphrase
the first time when you run the above command. Just go
ahead and enter it - it _will_ prompt you the second time.
When the two match, all is good.

Of course, you need to share this database with the
remote side in another secure way (i.e. sending
pgp-encrypted mail). If you prefer to have each user
generate his/her own database, you can use the
init_conversation.py utility in the pyaxo repo
linked above.

The latest version of the script and database utility
can be found at:
https://github.com/rxcomm/weechat-axolotl
"""


import weechat, string, os, re
from pyaxo import Axolotl
from binascii import b2a_base64, a2b_base64

script_options = {
    "message_indicator" : "(enc) ",
    "statusbar_indicator" : "(PFS encrypted) ",
}

def getPasswd(username):
    """modify as appropriate"""
    return username+'123'

def decrypt(data, msgtype, servername, args):
  global decrypted
  hostmask, chanmsg = string.split(args, "PRIVMSG ", 1)
  channelname, message = string.split(chanmsg, " :", 1)
  if re.match(r'^\[\d{2}:\d{2}:\d{2}]\s', message):
    timestamp = message[:11]
    message = message[11:]
  else:
    timestamp = ''
  if channelname[0] == "#":
    username=channelname
  else:
    username, rest = string.split(hostmask, "!", 1)
    username = username[1:]
  nick = channelname.strip()
  if os.path.exists(weechat_dir + '/' + username + '.db'):
    a = Axolotl(nick, dbname=weechat_dir+'/'+username+'.db', dbpassphrase=getPasswd(username))
    a.loadState(nick, username)
    decrypted = a.decrypt(a2b_base64(message))
    a.saveState()
    del a
    if decrypted == "":
      return args
    decrypted = ''.join(c for c in decrypted if ord(c) > 31 or ord(c) == 9 or ord(c) == 2 or ord(c) == 3 or ord(c) == 15)
    return hostmask + "PRIVMSG " + channelname + " :" + chr(3) + "04" + weechat.config_get_plugin("message_indicator") + chr(15) + timestamp + decrypted
  else:
    return args

def encrypt(data, msgtype, servername, args):
  global encrypted
  pre, message = string.split(args, ":", 1)
  prestr=pre.split(" ")
  username=prestr[-2]
  buf = weechat.current_buffer()
  nick = weechat.buffer_get_string(buf, 'localvar_nick')
  if os.path.exists(weechat_dir + '/' + username + '.db'):

    a = Axolotl(nick, dbname=weechat_dir+'/'+username+'.db', dbpassphrase=getPasswd(username))
    a.loadState(nick, username)
    encrypted = a.encrypt(message)
    if encrypted == '':
        return args
    encrypted = b2a_base64(encrypted)
    a.saveState()
    del a
    encrypted = encrypted.replace("\n","")
    final_msg = pre + ":" +encrypted
    if len(encrypted) > 400:
      # I arrived at this next equation heuristically. If it doesn't work, let me know
      # and I will work on it some more. -DRA
      numsplits = 2*int(len(encrypted)/400) + 1
      splitmsg=string.split(message," ")
      cutpoint=int(len(splitmsg)/numsplits)
      encrypted_list = []
      for i in range(numsplits+1):
        if min((i+1)*cutpoint, len(splitmsg)) == (i+1)*cutpoint:
          segment = string.join(splitmsg[i*cutpoint:(i+1)*cutpoint]," ") + "\n"
          a = Axolotl(nick, dbname=weechat_dir+'/'+username+'.db', dbpassphrase=getPasswd(username))
          a.loadState(nick, username)
          encrypted = b2a_base64(a.encrypt(segment))
          a.saveState()
          del a
          valid_segment = True
        else:
          segment = string.join(splitmsg[i*cutpoint:]," ")
          if segment.strip() is None or len(segment) == 0:
            valid_segment = False
          else:
            a = Axolotl(nick, dbname=weechat_dir+'/'+username+'.db', dbpassphrase=getPasswd(username))
            a.loadState(nick, username)
            encrypted = b2a_base64(a.encrypt(segment))
            a.saveState()
            del a
            valid_segment = True
        encrypted = encrypted.replace("\n","")
        if valid_segment:
          encrypted_list += [encrypted]
      final_msg = ''
      for item in encrypted_list:
        final_msg = final_msg + pre + ":" + item + '\n'
    return final_msg
    return encrypted
  else:
    return args

def update_encryption_status(data, signal, signal_data):
    buffer = signal_data
    weechat.bar_item_update('axolotl')
    return weechat.WEECHAT_RC_OK

def encryption_statusbar(data, item, window):
    if window:
      buf = weechat.window_get_pointer(window, 'buffer')
    else:
      buf = weechat.current_buffer()
    if os.path.exists(weechat_dir + '/' + \
         weechat.buffer_get_string(buf, 'short_name') + '.db'):
      return weechat.config_get_plugin("statusbar_indicator")
    else:
      return ""

# register plugin
if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, \
                    SCRIPT_LICENSE, SCRIPT_DESC, "", "UTF-8"):
    weechat_dir = weechat.info_get("weechat_dir","")
    key_dir = weechat.config_get_plugin('key_dir')
    version = weechat.info_get("version_number", "") or 0
    if int(version) < 0x00030000:
      weechat.prnt("", "%s%s: WeeChat 0.3.0 is required for this script."
              % (weechat.prefix("error"), SCRIPT_NAME))
    else:
      weechat.bar_item_new('axolotl', 'encryption_statusbar', '')
      for option, default_value in script_options.iteritems():
          if not weechat.config_is_set_plugin(option):
                  weechat.config_set_plugin(option, default_value)

      # register the modifiers
      weechat.hook_modifier("irc_in_privmsg", "decrypt", "")
      weechat.hook_modifier("irc_out_privmsg", "encrypt", "")
      weechat.hook_signal("buffer_switch","update_encryption_status","")
