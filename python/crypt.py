#!/usr/bin/python
# ==============================================================
# crypt.py written 08/2008 by blackpenguin <nlissne@linux01.org>
# ==============================================================
# License     : Public Domain
# Description : encrypt/decrypt PRIVMSGs in WeeChat using openssl
#
# Version     : 0.02
#
# This plugin uses openssl to encrypt/decrypt messages you send
# or receive with weechat. Due to the very simple method 
# used it should be easy to port this plugin to any other 
# IRC client. 
#
# The default encryption algorithm is blowfish, but you can
# easily change it to any other cipher your openssl offers.
# Read output of "openssl -h" to find out, which ciphers are
# supported (also depends on your kernel)
CIPHER="blowfish"
# 
# To activate encryption for a given server.user just
# put a file called "cryptkey.server.user" into 
# your weechat-directory, containing the passphrase
# to use for encryption/decryption 
# example: if you have exchanged a secret key with me,
# you would put it in a file called 
# cryptkey.freenode.blackpenguin in your weechat_dir
#
# Of course, you need to share this keyfile with the 
# remote side in another secure way (i.e. sending
# pgp-encrypted mail)
#
# I might implement a /crypt command to activate/deactivate
# encryption later, but for now the method used works for me.
#
# HISTORY:
# version 0.01 initial version
#
# version 0.02 switched from os.environ["HOME"] + "/.weechat" 
#              to get_info("weechat_dir")

import weechat, string, os


def decrypt(server, args):
  pre, middle, message = string.split(args, ":", 2)
  midstr=middle.split(" ")
  username=midstr[-2]
  if os.path.exists(weechat_dir + "/cryptkey." + server + "." + username):
    cin, cout = os.popen2("openssl enc -d -a -" + CIPHER + " -pass file:" + weechat_dir + "/cryptkey." + server + "." + username + " 2>/dev/null")
    cin.write(message.replace("|","\n"))
    cin.close()
    decrypted = cout.read()
    sts = cout.close()
    if decrypted == "":
      return pre + ":" + middle + ":" + message
    return pre + ":" + middle + ":" + chr(3) + "04* crypted * " + chr(15) + decrypted 
  else:
    return pre + ":" + middle + ":" + message
    
def encrypt(server, args):
  pre, message = string.split(args, ":", 1)
  prestr=pre.split(" ")
  username=prestr[-2]
  if os.path.exists(weechat_dir + "/cryptkey."  + server + "." + username):
    cin, cout = os.popen2("openssl enc -a -" + CIPHER + " -pass file:" + weechat_dir + "/cryptkey." + server + "." + username + " 2>/dev/null")
    cin.write(message)
    cin.close()
    encrypted = cout.read()
    encrypted = encrypted.replace("\n","|")
    cout.close()
    weechat.print_infobar(0,"* sent encrypted * ")
    return pre + ":" + encrypted
  else:
    weechat.remove_infobar(0)
    return pre + ":" + message



# register the plugin
weechat.register("crypt", "0.02", "", "encrypt/decrypt PRIVMSGs")
weechat_dir = weechat.get_info("weechat_dir")

# register the modifiers
weechat.add_modifier("irc_in", "privmsg", "decrypt")
weechat.add_modifier("irc_out", "privmsg", "encrypt")

