# ==============================================================
# crypt.py written 2008 by blackpenguin <nlissne@linux01.org>
# ==============================================================
# License     : GPL3
# Description : encrypt/decrypt PRIVMSGs in WeeChat using 
#               a pre-shared key and openssl
#
# *this version is for the upcoming weechat-0.3.0 only*
#
version="1.3"
#
# This plugin uses openssl to encrypt/decrypt messages you send
# or receive with weechat. Due to the very simple method 
# used it should be easy to port this plugin to any other 
# IRC client. 
#
# The default encryption algorithm is blowfish, but you can
# easily change it to any other cipher your openssl offers.
# Read output of "openssl -h" to find out which ciphers are
# supported (also depends on your kernel!)
CIPHER="blowfish"
# 
# To activate encryption for a given user just
# put a file called "cryptkey.username" into 
# your weechat-directory, containing the passphrase
# to use for encryption/decryption 
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

import weechat, string, os, subprocess

def decrypt(data, msgtype, servername, args):
  hostmask, chanmsg = string.split(args, "PRIVMSG ", 1)
  channelname, message = string.split(chanmsg, " :", 1)
  if channelname[0] == "#":
    username=channelname
  else:
    username, rest = string.split(hostmask, "!", 1)
    username = username[1:]
  if os.path.exists(weechat_dir + "/cryptkey." + username):
    p = subprocess.Popen(["openssl", "enc", "-d", "-a", "-" + CIPHER, "-pass" ,"file:" + weechat_dir + "/cryptkey." + username], bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    p.stdin.write("U2FsdGVkX1" + message.replace("|","\n"))
    p.stdin.close()
    decrypted = p.stdout.read()
    p.stdout.close()
    if decrypted == "":
      return args
    return hostmask + "PRIVMSG " + channelname + " :" + chr(3) + "04* crypted * " + chr(15) + decrypted 
  else:
    return args
    
def encrypt(data, msgtype, servername, args):
  pre, message = string.split(args, ":", 1)
  prestr=pre.split(" ")
  username=prestr[-2]
  if os.path.exists(weechat_dir + "/cryptkey." + username):
    p = subprocess.Popen(["openssl", "enc", "-a", "-" + CIPHER, "-pass" ,"file:" + weechat_dir + "/cryptkey." + username], bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    p.stdin.write(message)
    p.stdin.close()
    encrypted = p.stdout.read()
    p.stdout.close()
    encrypted = encrypted.replace("\n","|")
    if len(encrypted) > 400:
      splitmsg=string.split(message," ")
      cutpoint=len(splitmsg)/2
      p = subprocess.Popen(["openssl", "enc", "-a", "-" + CIPHER, "-pass" ,"file:" + weechat_dir + "/cryptkey." + username], bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
      p.stdin.write(string.join(splitmsg[:cutpoint]," ") + "\n")
      p.stdin.close()
      encrypted = p.stdout.read()
      p.stdout.close()
      encrypted = encrypted.replace("\n","|")
      p = subprocess.Popen(["openssl", "enc", "-a", "-" + CIPHER, "-pass" ,"file:" + weechat_dir + "/cryptkey." + username], bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
      p.stdin.write( string.join(splitmsg[cutpoint:]," ") )
      p.stdin.close()
      encrypted2 = p.stdout.read()
      p.stdout.close()
      encrypted2 = encrypted2.replace("\n","|")
      encrypted = encrypted + "\n" + pre + ":" + encrypted2[10:]
    return pre + ":" + encrypted[10:]
  else:
    return args

# for subprocess.Popen call
PIPE=-1

# register plugin
weechat.register("crypt", "Nicolai Lissner", version, "GPL3",  "encrypt/decrypt PRIVMSGs", "", "UTF-8")
weechat_dir = weechat.info_get("weechat_dir","")

# register the modifiers
weechat.hook_modifier("irc_in_privmsg", "decrypt", "")
weechat.hook_modifier("irc_out_privmsg", "encrypt", "")
