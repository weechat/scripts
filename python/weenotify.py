# BSD 2-Clause License
#
# Copyright (c) 2018, Elia El Lazkani
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Local mode dependencies:
  - weechat
  - dbus-python
  - notify2

Remote mode dependencies:
  - weechat

Server mode dependencies:
  - dbus-python
  - notify2

This script acts as both server and weechat plugin. One can configure it to run
locally on the box in which case it will use *notify2* to send notifications
through dbus to the user. Or, one can run it in remote mode where both
the _host_ and the _port_ need to be configured to send notifications to the server.

If you are running weechat in an ssh session, you can do the following:
> ssh -R 5431:localhost:5431 user@host

The above will ssh tunnel port 5431 between guest and host and notifications can be
sent to the server running locally on your machine.

To run the server, do the following:
> python weenotify.py -s

One can get the full script help print with:
> python weenotify.py -h
"""

import json
import socket
import argparse

try:
    import notify2 as Notify
    import dbus
    notify_imported = True
    dbus_imported = True
except ImportError:
    try:
        import dbus
        dbus_imported = True
    except ImportError:
        dbus_imported = False
    notify_imported = False

try:
    import weechat as w
    weechat_imported = True
except ImportError:
    weechat_imported = False

SCRIPT_NAME = "weenotify"
SCRIPT_AUTHOR = "Elia El Lazkani <elia.el.lazkani@gmail.com>"
SCRIPT_VERSION = "0.4"
SCRIPT_LICENSE = "BSD-2-Clause"
SCRIPT_DESCRIPTION = "Plugin/Server to send/receive notifications and display them"

def listener(sockt):
    """ Method to handle incoming data from client """
    conn, addr = sockt.accept()
    try:
        data = ""
        _partial = conn.recv(1024).decode('utf-8')
        while _partial:
            data += _partial
            _partial = conn.recv(1024).decode('utf-8')
    except Exception:
        conn.close()
        return

    if data:
        print("{}: {}".format(addr, data.strip('\n')))
        notify(json.loads(data.strip()))

def server(host, port):
    """ Method to run the server in a loop """
    print("Starting server...")
    host = host if host else ''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(5)
    if host:
        print("Server listening on {}:{}...".format(host, port))
    else:
        print("Server listening locally on port {}...".format(port))

    try:
        while True:
            listener(s)
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        s.close()

def notify(data):
    """ Method to notify the user through dbus """
    if data['prefix'] != '--':
        try:
            msg = "{} => {}: {}".format(data['buffer'],
                                        data['prefix'],
                                        data['message'])
        except UnicodeEncodeError:
            # Yey to python2
            msg = "{} => {}: {}".format(data['buffer'],
                                        data['prefix'],
                                        data['message'].encode('utf-8'))
    else:
        try:
            msg = "{} => {}".format(data['buffer'],
                                    data['message'])
        except UnicodeEncodeError:
            # Woohoo python2
            msg = "{} => {}".format(data['buffer'],
                                    data['message'].encode('utf-8'))
    Notify.init(SCRIPT_NAME)
    notification = Notify.Notification(data['type'], msg)
    try:
        notification.show()
    except dbus.exceptions.DBusException as e:
        print(e)
        pass

def local_notify(data):
    """ Method to send notification locally on the host """
    if notify_imported:
        notify(data)
    else:
        if dbus_imported:
            w.prnt("", "notify2 could not be imported, disabling {}"
                .format(SCRIPT_NAME))
        else:
            w.prnt("", "notify2 could not be imported due to missing dbus-python,"
                   "disabling {}".format(SCRIPT_NAME))
        w.config_set_plugin('enable', 'off')

def send(host, port, msg):
    """ Method to send data to the server for notification display """
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        c.connect((host, port))
    except Exception:
        c.close()
        return
    message = "{}".format(json.dumps(msg))
    message = str.encode(message, 'utf-8')
    c.sendall(message)
    c.close()

def on_notify(data, buffer, date, tags, displayed,
              highlight, prefix, message):
    """ Method to take action on client notification """
    enable = w.config_get_plugin('enable')
    if enable.lower() == 'on':
        data = weechat_parser(data, buffer, date, tags, displayed,
                              highlight, prefix, message)
        if data:
            mode = w.config_get_plugin('mode')
            if mode.lower() == 'remote':
                host = w.config_get_plugin('host')
                port = int(w.config_get_plugin('port'))
                send(host, port, data)
            else:
                local_notify(data)
    return w.WEECHAT_RC_OK

def weechat_parser(data, buffer, date, tags, displayed,
                   highlight, prefix, message):
    """ Method to parte data coming from weechat and take action on it """
    buffer_name = w.buffer_get_string(buffer, 'short_name')
    if "NOTICE" in data and buffer_name != "highmon":
        if buffer_name == prefix:
            buffer_name = data
        return { 'buffer': buffer_name,
                 'type': data,
                 'prefix': prefix,
                 'message': message }
    elif "PRIVMSG" in data and "irc_notice" not in tags:
        return { 'buffer': buffer_name,
                 'type': data,
                 'prefix': prefix,
                 'message': message }
    elif "MSG" in data and int(highlight) and \
         "irc_notice" not in tags:
        return { 'buffer': buffer_name,
                 'type': data,
                 'prefix': prefix,
                 'message': message }

def client():
    """ Method to register the plugin and hook into weechat """
    settings = {
        'enable': {
            'description': 'Enable/Disable notifications.',
            'values': ['off', 'on'],
            'default': 'off'
        },
        'mode': {
            'description': 'Set whether notifications need to be'
            'sent locally or to an external server.',
            'values': ['local', 'remote'],
            'default': 'local'
        },
        'host': {
            'description': 'Set the server host to send notifications to.',
            'values': None,
            'default': 'localhost'
        },
        'port': {
            'description': 'Set the server port to use to send notifcation.',
            'values': None,
            'default': '5431'
        }
    }

    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                  SCRIPT_DESCRIPTION, '', ''):
        for option, value in settings.items():
            if not w.config_is_set_plugin(option):
                w.config_set_plugin(option, value['default'])
            if value.get('values', None):
                w.config_set_desc_plugin(option, '{} (values: [{}], default: {})'.format(
                    value['description'], '/'.join(value['values']), value['default']))
            else:
                w.config_set_desc_plugin(option, '{} (default: {})'.format(
                    value['description'], value['default']))
        w.hook_print('', 'notify_message', '', 1, 'on_notify', 'MSG')
        w.hook_print('', 'notify_private', '', 1, 'on_notify', 'PRIVMSG')
        w.hook_print('', 'irc_notice', '', 1, 'on_notify', 'NOTICE')

def argument_parse():
    """ Method to parse command line arguments """
    parser = argparse.ArgumentParser(
        description=SCRIPT_DESCRIPTION)

    parser.add_argument(
        '-s', '--server', action='store_true',
        help='Run in server mode.')
    parser.add_argument(
        '-H', '--host', type=str, default='',
        help='The host/IP to bind to.')
    parser.add_argument(
        '-p', '--port', type=int, default=5431,
        help='The port to listen to.')
    parser.add_argument(
        '-V', '--version', action='version',
        version='%(prog)s {}'.format(SCRIPT_VERSION),
        help='Prints version.')
    return parser

if __name__ == '__main__':
    parser = argument_parse()
    args = parser.parse_args()
    if args.server:
        if notify_imported:
            server(args.host, args.port)
        else:
            if dbus_imported:
                print("notify2 could not be imported")
            else:
                print("notify2 was not imported due to missing dbus-python")
    else:
        if weechat_imported:
            client()
        else:
            print("weechat could not be imported, make sure weechat is running this")
