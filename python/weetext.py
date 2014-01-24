# ===============================================================

# Copyright (C) 2014 by David R. Andersen and Tycho Andersen

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Development repository at: https://github.com/rxcomm/weeText/

SCRIPT_NAME    = "weetext"
SCRIPT_AUTHOR  = "David R. Andersen <k0rx@RXcomm.net>, Tycho Andersen <tycho@tycho.ws>"
SCRIPT_VERSION = "0.1.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "SMS Text Messaging script for Weechat using Google Voice"

"""
This script implements chatting via text message with Weechat.

Email and password should be configured (either by editing the script
itself before loading or adding options to plugins.conf). For using
secure passwords, see the weechat /secure command.

To initiate a text message session with someone new, that isn't currently
in your weeText buffer list, in the weeText buffer type the command:

text <10 digit phone number>

This will pop open a new buffer.

You can also send text messages to multiple numbers. The syntax is (from
the weeText buffer):

multi <number1>,<number2>,...

This will pop open a new multi-text buffer.

I've also added optional symmetric-key encryption using OpenSSL. This is
essentially a wholesale copy of the encrypt() and decrypt() methods from
the weechat crypt.py script. Thanks to the authors for that!

Todo:
1. Add buffer for texting multiple parties at the same time.

"""

import weechat
import sys
import os
import glob
import re
import cPickle
import subprocess
import random
import string
from googlevoice import Voice
from googlevoice.util import input
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup, SoupStrainer

script_options = {
    "email" : "", # GV email address
    "passwd" : "", # GV password - can use /secure
    "poll_interval" : "120", # poll interval for receiving messages (sec)
    "encrypt_sms" : "True",
    "key_dir" : "/cryptkey",
    "cipher" : "aes-256-cbc",
    "message_indicator" : "(enc) ",
}

conversation_map = {}
number_map = {}
conv = ''

class Conversation(object):
    def __init__(self, conv_id, number, messages):
        self.conv_id = conv_id
        self.number = number
        self.messages = messages

    def new_messages(self, other):
        assert len(self.messages) <= len(other.messages)
        return other.messages[len(self.messages):]

    def __iter__(self):
        return iter(reversed(self.messages))

def renderConversations(unused, command, return_code, out, err):
    global conversation_map
    global conv

    if return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt("", "Error with command '%s'" % command)
        return weechat.WEECHAT_RC_OK
    if return_code > 0:
        weechat.prnt("", "return_code = %d" % return_code)
    if out != '':
        conv += out
        if return_code == weechat.WEECHAT_HOOK_PROCESS_RUNNING:
            weechat.prnt('', 'getting more data')
            return weechat.WEECHAT_RC_OK
    if err != "":
        weechat.prnt("", "stderr: %s" % err)
        return weechat.WEECHAT_RC_OK

    try:
        conversations = reversed(cPickle.loads(conv))
    except EOFError:
        weechat.prnt('', 'wtrecv returned garbage')
        return weechat.WEECHAT_RC_OK

    for conversation in conversations:
        if not conversation.conv_id in conversation_map:
            conversation_map[conversation.conv_id] = conversation
            msgs = conversation.messages
        else:
            old = conversation_map[conversation.conv_id]
            conversation_map[conversation.conv_id] = conversation
            msgs = old.new_messages(conversation)
        for msg in msgs:
            if not conversation.number in number_map and msg['from'] != 'Me:':
                number_map[conversation.number] = msg['from']
        for msg in msgs:
            if conversation.number in number_map:
                buf = weechat.buffer_search('python', number_map[conversation.number][:-1])
                if not buf:
                    buf = weechat.buffer_new(number_map[conversation.number][:-1],
                                             "textOut", "", "buffer_close_cb", "")
            else:
                buf = weechat.buffer_search('python', 'Me')
                if not buf:
                    buf = weechat.buffer_new('Me', "textOut", "", "buffer_close_cb", "")
            if weechat.config_get_plugin('encrypt_sms') == 'True':
                msg['text'] = decrypt(msg['text'], buf)
            nick = msg['from'][:-1].strip()
            tags = 'notify_private,nick_' + msg['from'][:-1].strip()
            tags += ',log1,prefix_nick_' + weechat.info_get('irc_nick_color_name', nick)
            nick = msg['from'][:-1].strip()
            weechat.prnt_date_tags(buf, 0, tags, '\x03' + weechat.info_get('irc_nick_color', nick)
                                   + nick + '\t' + msg['text'])
    conv = ''
    callGV()
    return weechat.WEECHAT_RC_OK

def textOut(data, buf, input_data):
    global number_map
    number = None
    for num, dest in number_map.iteritems():
        if dest[:-1] == weechat.buffer_get_string(buf, 'name'):
            number = num[2:]
    if not number:
        number = weechat.buffer_get_string(buf, 'name')[2:]
    if weechat.config_get_plugin('encrypt_sms') == 'True':
        input_data = encrypt(input_data, buf)
    msg_id = ''.join(random.choice(string.lowercase) for x in range(4))
    callGV(buf=buf, number=number, input_data=input_data, msg_id=msg_id, send=True)
    return weechat.WEECHAT_RC_OK

def multiText(data, buf, input_data):
    global number_map
    numbers = data.split(',')
    if weechat.config_get_plugin('encrypt_sms') == 'True':
        input_data = encrypt(input_data, buf)
    for number in numbers:
        msg_id = ''.join(random.choice(string.lowercase) for x in range(4))
        callGV(buf=buf, number=number, input_data=input_data, msg_id=msg_id, send=True)
    return weechat.WEECHAT_RC_OK

def sentCB(buf_name, command, return_code, out, err):
    if return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt("", "Error with command '%s'" % command)
        return weechat.WEECHAT_RC_OK
    if return_code > 0:
        weechat.prnt("", "return_code = %d" % return_code)
    if out != "":
        tags = 'notify_message'
        weechat.prnt_date_tags(weechat.buffer_search('python', buf_name), 0, tags, out)
    if err != "":
        weechat.prnt("", "stderr: %s" % err)
    return weechat.WEECHAT_RC_OK

def gvOut(data, buf, input_data):
    if input_data[:4] == 'text' and buf == weechat.buffer_search('python', 'weeText'):
        buffer = weechat.buffer_new("+1"+input_data[5:], "textOut", "", "buffer_close_cb", "")
    if input_data[:5] == 'multi' and buf == weechat.buffer_search('python', 'weeText'):
        num_list = input_data[6:].split(',')
        nums = ''
        for num in num_list:
            nums += '+' + num[-4:]
        nums = nums[1:]
        buffer = weechat.buffer_new('m:' + nums, "multiText", input_data[6:], "buffer_close_cb", "")
    return weechat.WEECHAT_RC_OK

def buffer_input_cb(data, buf, input_data):
    # ...
    return weechat.WEECHAT_RC_OK

def buffer_close_cb(data, buf):
    return weechat.WEECHAT_RC_OK

def encrypt(message, buf):
  username=weechat.buffer_get_string(buf, 'name')
  if os.path.exists(weechat_dir + key_dir + "/cryptkey." + username):
    p = subprocess.Popen(["openssl", "enc", "-a", "-" + weechat.config_get_plugin("cipher"),
                          "-pass" ,"file:" + weechat_dir + key_dir + "/cryptkey." + username],
                          bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    p.stdin.write(message)
    p.stdin.close()
    encrypted = p.stdout.read()
    p.stdout.close()
    encrypted = encrypted.replace("\n","|")
    return encrypted[10:]
  else:
    return message

def decrypt(message, buf):
  username=weechat.buffer_get_string(buf, 'name')
  if os.path.exists(weechat_dir + key_dir + "/cryptkey." + username):
    p = subprocess.Popen(["openssl", "enc", "-d", "-a", "-" + weechat.config_get_plugin("cipher"),
                          "-pass" ,"file:" + weechat_dir + key_dir + "/cryptkey." + username],
                          bufsize=4096, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    p.stdin.write("U2FsdGVkX1" + message.replace("|","\n"))
    p.stdin.close()
    decrypted = p.stdout.read()
    p.stdout.close()
    if decrypted == "":
      return message
    decrypted = ''.join(c for c in decrypted if ord(c) > 31 or ord(c) == 9 or ord(c) == 2
                or ord(c) == 3 or ord(c) == 15)
    return '\x19' + weechat.color('lightred') + weechat.config_get_plugin("message_indicator") + '\x1C' + decrypted
  else:
    return message

def update_encryption_status(data, signal, signal_data):
    buffer = signal_data
    weechat.bar_item_update('encryption')
    return weechat.WEECHAT_RC_OK

def encryption_statusbar(data, item, window):
    if window:
      buf = weechat.window_get_pointer(window, 'buffer')
    else:
      buf = weechat.current_buffer()
    if os.path.exists(weechat_dir + key_dir + "/cryptkey." + weechat.buffer_get_string(buf, "short_name")):
      return weechat.config_get_plugin("statusbar_indicator")
    else:
      return ""

def checkWTrecv(*args):
    tmp = os.popen('ps -Af').read()
    if not tmp.count('wtrecv'):
        callGV()
    return weechat.WEECHAT_RC_OK


def callGV(buf=None, number=None, input_data=None, msg_id=None, send=False):
    if send:
        send_hook = weechat.hook_process_hashtable(weechat_dir + '/python/wtsend.py',
                    { 'stdin': '' }, 0, 'sentCB', weechat.buffer_get_string(buf, 'name'))
        proc_data = email + '\n' + passwd + '\n' + number + '\n' +\
                    input_data + '\n' + msg_id + '\n'
        weechat.hook_set(send_hook, 'stdin', proc_data)
    else:
        proc_data = email + '\n' + passwd + '\n' +\
                    weechat.config_get_plugin('poll_interval') + '\n'
        recv_hook = weechat.hook_process_hashtable(weechat_dir + '/python/wtrecv.py',
                { 'stdin': '' }, 0, 'renderConversations', '')
        weechat.hook_set(recv_hook, 'stdin', proc_data)

PIPE=-1

# register plugin
if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "UTF-8"):
    buffer = weechat.buffer_new("weeText", "gvOut", "", "buffer_close_cb", "")
    weechat_dir = weechat.info_get("weechat_dir","")
    key_dir = weechat.config_get_plugin("key_dir")
    weechat.bar_item_new('encryption', 'encryption_statusbar', '')
    for option, default_value in script_options.iteritems():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)

    # get email/passwd and pass to other script
    email=weechat.config_get_plugin('email')
    passwd = weechat.config_get_plugin('passwd')
    if re.search('sec.*data', passwd):
        passwd=weechat.string_eval_expression(passwd, {}, {}, {})

    # write the helper files
    with open(weechat_dir + '/python/wtrecv.py', 'w') as f:
        f.write("""#!/usr/bin/env python

import sys
import cPickle
import time
import re
import os
import glob
from googlevoice import Voice
from googlevoice.util import input
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup, SoupStrainer

user_path = os.path.expanduser('~')

class Conversation(object):
    def __init__(self, conv_id, number, messages):
        self.conv_id = conv_id
        self.number = number
        self.messages = messages

    def new_messages(self, other):
        assert len(self.messages) <= len(other.messages)
        return other.messages[len(self.messages):]

    def __iter__(self):
        return iter(reversed(self.messages))

class SMS:

    def getsms(self):
        # We could call voice.sms() directly, but I found this does a rather
        # inefficient parse of things which pegs a CPU core and takes ~50 CPU
        # seconds, while this takes no time at all.
        data = voice.sms.datafunc()
        data = re.search(r'<html><\!\[CDATA\[([^\]]*)', data, re.DOTALL).groups()[0]

        divs = SoupStrainer(['div', 'input'])
        tree = BeautifulSoup(data, parseOnlyThese=divs)

        convos = []
        conversations = tree.findAll("div", attrs={"id" : True},recursive=False)
        for conversation in conversations:
            inputs = SoupStrainer('input')
            tree_inp = BeautifulSoup(str(conversation),parseOnlyThese=inputs)
            phone = tree_inp.find('input', "gc-quickcall-ac")['value']

            smses = []
            msgs = conversation.findAll(attrs={"class" : "gc-message-sms-row"})
            for row in msgs:
                msgitem = {"id" : conversation["id"]}
                spans = row.findAll("span", attrs={"class" : True}, recursive=False)
                for span in spans:
                    cl = span["class"].replace('gc-message-sms-', '')
                    msgitem[cl] = (" ".join(span.findAll(text=True))).strip()
                if msgitem["text"]:
                    msgitem["text"] = BeautifulStoneSoup(msgitem["text"],
                                      convertEntities=BeautifulStoneSoup.HTML_ENTITIES
                                      ).contents[0]
                    msgitem['phone'] = phone
                    smses.append(msgitem)
            convos.append(Conversation(conversation['id'], phone, smses))
        print cPickle.dumps(convos)

if __name__ == '__main__':

    email = sys.stdin.readline().strip()
    passwd = sys.stdin.readline().strip()
    poll_interval = sys.stdin.readline().strip()

    time.sleep(float(poll_interval))

    # create voice instance if no texts are being sent
    while True:
        f = glob.glob(user_path + '/.weechat/.gvlock*')
        if f == []:
            voice = Voice()
            voice.login(email=email, passwd=passwd)
            sms = SMS()
            sms.getsms()
            break
        else:
            time.sleep(1)
""")
    os.chmod(weechat_dir + '/python/wtrecv.py', 0755)

    with open(weechat_dir + '/python/wtsend.py', 'w') as f:
        f.write("""#!/usr/bin/env python

import sys
import os
from googlevoice import Voice
from googlevoice.util import input

# read the credentials, payload, and msg_id from stdin
email = sys.stdin.readline().strip()
passwd = sys.stdin.readline().strip()
number = sys.stdin.readline().strip()
payload = sys.stdin.readline().strip()
msg_id = sys.stdin.readline().strip()

user_path = os.path.expanduser('~')
open(user_path + '/.weechat/.gvlock.' + msg_id, 'a').close()

try:
    voice = Voice()
    voice.login(email, passwd)
    voice.send_sms(number, payload)
    print '<message sent>'
except:
    print '<message NOT sent!>'

os.remove(user_path + '/.weechat/.gvlock.' + msg_id)
""")
    os.chmod(weechat_dir + '/python/wtsend.py', 0755)

    # remove any old .gvlock.* files
    for gvlockfile in glob.glob(weechat_dir + '/.gvlock.*'):
        os.remove(gvlockfile)

    # register the hooks
    weechat.hook_signal("buffer_switch","update_encryption_status","")
    callGV()

    # make sure we are receiving data
    weechat.hook_timer(600000, 0, 0, 'checkWTrecv', '')
