# ===============================================================
# crypt.py (c) 2008-2012 by Nicolai Lissner <nlissne@linux01.org>
# ===============================================================
SCRIPT_NAME    = "crypt"
SCRIPT_AUTHOR  = "Nicolai Lissner <nlissne@linux01.org>"
SCRIPT_VERSION = "1.4.4"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "encrypt/decrypt PRIVMSGs using a pre-shared key and openssl"

#
# This plugin uses openssl to encrypt/decrypt messages you send
# or receive with weechat. Due to the very simple method
# used it should be easy to port this plugin to any other
# IRC client.
#
# The default encryption algorithm is blowfish, but you can
# change it to any other cipher your openssl offers.
# Read output of "openssl -h" to find out which ciphers are
# supported (also depends on your kernel!)
#
# To activate encryption for a given user just
# put a file called "cryptkey.username" into
# your weechat-directory, containing the passphrase
# to use for encryption/decryption
#
# you can add 'encryption' to
# weechat.bar.status.items to have an indication
# that the message you are going to send is encrypted
# (i.e. a keyfile exists)
#
# You can activate encryption on irc-channels, too,
# just use cryptkey.#channelname as keyfile then.
#
# example: if you have exchanged a secret key with me,
# you would put it in a file called
# cryptkey.blackpenguin in your weechat_dir
#
# Of course, you need to share this keyfile with the
# remote side in another secure way (i.e. sending
# pgp-encrypted mail)

import weechat, string, os, subprocess, re

script_options = {
    "message_indicator" : "(enc) ",
    "statusbar_indicator" : "(encrypted) ",
    "cipher" : "blowfish",
}

def decrypt(data, msgtype, servername, args):
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
  if os.path.exists(weechat_dir + "/cryptkey." + username):
    p = subprocess.Popen(["openssl", "enc", "-d", "-a", "-" + weechat.config_get_plugin("cipher"), "-pass" ,"file:" + weechat_dir + "/cryptkey." + username], bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    p.stdin.write("U2FsdGVkX1" + message.replace("|","\n"))
    p.stdin.close()
    decrypted = p.stdout.read()
    p.stdout.close()
    if decrypted == "":
      return args
    decrypted = ''.join(c for c in decrypted if ord(c) > 31 or ord(c) == 9 or ord(c) == 2 or ord(c) == 3 or ord(c) == 15)
    return hostmask + "PRIVMSG " + channelname + " :" + chr(3) + "04" + weechat.config_get_plugin("message_indicator") + chr(15) + timestamp + decrypted
  else:
    return args

def encrypt(data, msgtype, servername, args):
  pre, message = string.split(args, ":", 1)
  prestr=pre.split(" ")
  username=prestr[-2]
  if os.path.exists(weechat_dir + "/cryptkey." + username):
    p = subprocess.Popen(["openssl", "enc", "-a", "-" + weechat.config_get_plugin("cipher"), "-pass" ,"file:" + weechat_dir + "/cryptkey." + username], bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    p.stdin.write(message)
    p.stdin.close()
    encrypted = p.stdout.read()
    p.stdout.close()
    encrypted = encrypted.replace("\n","|")
    if len(encrypted) > 400:
      splitmsg=string.split(message," ")
      cutpoint=len(splitmsg)/2
      p = subprocess.Popen(["openssl", "enc", "-a", "-" + weechat.config_get_plugin("cipher"), "-pass" ,"file:" + weechat_dir + "/cryptkey." + username], bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
      p.stdin.write(string.join(splitmsg[:cutpoint]," ") + "\n")
      p.stdin.close()
      encrypted = p.stdout.read()
      p.stdout.close()
      encrypted = encrypted.replace("\n","|")
      p = subprocess.Popen(["openssl", "enc", "-a", "-" + weechat.config_get_plugin("cipher"), "-pass" ,"file:" + weechat_dir + "/cryptkey." + username], bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
      p.stdin.write( string.join(splitmsg[cutpoint:]," ") )
      p.stdin.close()
      encrypted2 = p.stdout.read()
      p.stdout.close()
      encrypted2 = encrypted2.replace("\n","|")
      encrypted = encrypted + "\n" + pre + ":" + encrypted2[10:]
    return pre + ":" + encrypted[10:]
  else:
    return args

def update_encryption_status(data, signal, signal_data):
    buffer = signal_data
    weechat.bar_item_update('encryption')
    return weechat.WEECHAT_RC_OK

def encryption_statusbar(data, item, window):
    if window:
      buf = weechat.window_get_pointer(window, 'buffer')
    else:
      buf = weechat.current_buffer()
    if os.path.exists(weechat_dir + "/cryptkey." + weechat.buffer_get_string(buf, "short_name")):
      return weechat.config_get_plugin("statusbar_indicator")
    else:
      return ""


# for subprocess.Popen call
PIPE=-1

# register plugin
if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "UTF-8"):
    weechat_dir = weechat.info_get("weechat_dir","")
    version = weechat.info_get("version_number", "") or 0
    if int(version) < 0x00030000:
      weechat.prnt("", "%s%s: WeeChat 0.3.0 is required for this script."
              % (weechat.prefix("error"), SCRIPT_NAME))
    else:
      weechat.bar_item_new('encryption', 'encryption_statusbar', '')
      for option, default_value in script_options.iteritems():
          if not weechat.config_is_set_plugin(option):
                  weechat.config_set_plugin(option, default_value)
      # register the modifiers
      weechat.hook_modifier("irc_in_privmsg", "decrypt", "")
      weechat.hook_modifier("irc_out_privmsg", "encrypt", "")
      weechat.hook_signal("buffer_switch","update_encryption_status","")
