# -*- coding: utf-8 -*-
# Author: Leon Bogaert <leon AT tim-online DOT nl>
# Author: Stacey Sheldon <stac AT solidgoldbomb DOT org>
# This Plugin Calls the libindicate bindings via python when somebody says your
# nickname, sends you a query, etc.
# To make it work, you may need to download:
#    python-indicate
#    python-dbus
#    wmctrl
# Requires Weechat 0.3.0
# Released under GNU GPL v2
#
# 2010-09-22, Leon <leon@tim-online.nl>:
#     version 0.0.1 Intial release
# 2013-04-14, Stacey Sheldon <stac@solidgoldbomb.org>
#     version 0.0.2 Added two-way sync between indications and weechat
# 2013-05-01, Stacey Sheldon <stac@solidgoldbomb.org>
#     version 0.0.3 More graceful handling of missing dependencies
# 2014-05-10, Sébastien Helleu <flashcode@flashtux.org>
#     version 0.0.4 Change hook_print callback argument type of
#                   displayed/highlight (WeeChat >= 1.0)
#
# @TODO: decide what to do if a user clicks an indicator an then start typing:
#        * leave indicators alone
#        * remove indicators in the "neighbourhood"
#        * On click group: remove all indicators

import dbus.service
import os

SCRIPT_NAME    = "windicate"
SCRIPT_AUTHOR  = "Leon Bogaert"
SCRIPT_VERSION = "0.0.4"
SCRIPT_LICENSE = "GPL"
SCRIPT_DESC    = "fills the indicate applet"

DBUS_CONNECTION = 'org.weechat.scripts.windicate'
DBUS_OBJ_PATH   = '/org/weechat/scripts/windicate'

class DBUSService(dbus.service.Object):
    def __init__(self, messageMenu):
        bus_name = dbus.service.BusName(DBUS_CONNECTION, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, DBUS_OBJ_PATH)
        self.messageMenu = messageMenu

    @dbus.service.method('org.weechat.scripts.windicate')
    def add_message(self, buffer, brief, sender, body):
        return self.messageMenu.add_message(buffer, brief, sender, body)

    @dbus.service.method('org.weechat.scripts.windicate')
    def del_messages(self, buffer):
        return self.messageMenu.del_messages(buffer)

class MessageMenu(object):
    def __init__(self, weechat_fifo, weechat_windowid):
        self.messages = []

        self.weechat_fifo = weechat_fifo
        self.weechat_windowid = weechat_windowid

        server = pyindicate.indicate_server_ref_default()
        server.set_type("message.im")
        server.set_desktop_file(self.desktop_file())
        server.connect("server-display", self.server_click)
        server.show()

    def desktop_file(self):
        DESKTOP_ENTRY = """\
[Desktop Entry]
Encoding=UTF-8
MultipleArgs=false
Terminal=true
Exec=weechat-curses
Icon=weechat
Type=Application
Categories=Network;IRCClient;
StartupNotify=false
Name=Weechat
GenericName=IRC Client
"""
        file = "/usr/share/applications/weechat.desktop"

        if os.path.isfile(file):
            return file

        import tempfile
        f = tempfile.NamedTemporaryFile(suffix='indicator', delete=False)
        f.write(DESKTOP_ENTRY)
        f.close()
        self.tmp_file = f

        return f.name

    def __del__(self):
        if self.tmp_file and os.file.exists(self.tmp_file):
            os.unlink(self.tmp_file)

    def raise_window(self):
        import subprocess
        try:
            retcode = subprocess.call('wmctrl -i -a %s' % self.weechat_windowid, shell=True)
            if retcode < 0:
                # print >>sys.stderr, "Child was terminated by signal", -retcode
                pass
            else:
                # print >>sys.stderr, "Child returned", retcode
                pass
        except OSError as e:
            # print >>sys.stderr, "Execution failed:", e
            pass

    def server_click(self, server, time):
        # tell weechat to select the first active buffer
        with open (self.weechat_fifo, 'a') as f:
            f.write ("irc.server.freenode */input jump_smart\n")
        # raise the weechat window to the foreground
        self.raise_window()

    def add_message(self, buffer, brief, sender, body):
        for message in self.messages:
            if message.buffer == buffer and message.sender == sender:
                return message.update_time()

        return self.messages.append(Message(self, buffer, brief, sender, body))

    def del_messages(self, buffer):
        # remove all pending indications for this buffer
        for message in self.messages:
            if message.buffer == buffer:
                self.messages.remove(message)
                message.indicator.hide()
        return True

class Message(object):
    def __init__(self, mm, buffer, brief, sender, message):
        # Setup the message
        try:
            # Ubuntu 9.10 and above
            indicator = pyindicate.Indicator()
        except:
            # Ubuntu 9.04
            indicator = pyindicate.IndicatorMessage()

        indicator.set_property("subtype", "im")
        indicator.set_property("sender", "%s (%s)" % (sender, brief))
        indicator.set_property("body", message)
        indicator.set_property_time("time", time())
        indicator.set_property('draw-attention', 'true');
        indicator.show()
        indicator.connect("user-display", self.message_clicked)

        self.indicator = indicator
        self.sender = sender
        self.message = message
        self.brief = brief
        self.messageMenu = mm
        self.buffer = buffer

    def update_time(self):
        self.indicator.set_property_time("time", time())

    def message_clicked(self, indicator, time):
        self.messageMenu.messages.remove(self)
        indicator.hide()
        # tell weechat to select the buffer that triggered this indication
        with open (self.messageMenu.weechat_fifo, 'a') as f:
            f.write ("core.weechat */buffer %s\n" % self.buffer)
        # raise the weechat window to the foreground
        self.messageMenu.raise_window()

class WindicateServer(object):
    def __init__(self, weechat_fifo, weechat_windowid):
        DBusGMainLoop(set_as_default=True)
        mm = MessageMenu(weechat_fifo, weechat_windowid)
        dbs = DBUSService(mm)

        loop = gobject.MainLoop()
        loop.run()

class Subprocess(object):
    p = None

    @classmethod
    def start(cls, fifo_filename, window_windowid):
        import inspect
        file = inspect.getfile(inspect.currentframe())

        import subprocess
        args = ["/usr/bin/python",
                file,
                fifo_filename,
                weechat_windowid]
        cls.p = subprocess.Popen(args)

    @classmethod
    def stop(cls):
        if cls.p != None:
            cls.p.terminate()

try:
    import weechat
except ImportError:
    """Ran from seperate process: start server!"""
    import gobject
    gobject.threads_init()
    import indicate as pyindicate
    import gtk
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from time import time
    import sys # argv

    # arguments: weechat_fifo_filename weechat_windowid
    ws = WindicateServer(sys.argv[1], sys.argv[2])    # doesn't return

##### FUNCTIONS #####

def weechat_script_end():
    Subprocess.stop()
    return weechat.WEECHAT_RC_OK

def notify_msg(data, bufferp, time, tags, display, is_hilight, prefix, msg):
    """Sends highlighted message to be printed on notification"""

    if ('notify_private' in tags and
        weechat.config_get_plugin('show_priv_msg') == "on") \
        or (int(is_hilight) and \
        weechat.config_get_plugin('show_hilights') == "on"):

        # grab the fully qualified buffer name so we can jump to it later
        buffer = weechat.buffer_get_string(bufferp, "name")

        # choose an appropriate brief name to display in the indicator applet
        if 'notify_private' in tags:
            brief = "private"
        else:
            # prefer short_name
            brief = weechat.buffer_get_string(bufferp, "short_name")
            if not brief:
                # fall back to full name
                brief = buffer

        if weechat.config_get_plugin('debug') == "on":
            print "buffer: " + buffer
            print "brief: " + brief
            print "prefix: " + prefix
            print "msg: " + msg

        # Create an object that will proxy for a particular remote object.
        bus = dbus.SessionBus()
        remote_object = bus.get_object(DBUS_CONNECTION, DBUS_OBJ_PATH)
        remote_object.add_message(buffer, brief, prefix, msg)

    return weechat.WEECHAT_RC_OK

def buffer_switched(data, signal, signal_data):
    buffer = weechat.buffer_get_string(signal_data, "name")
    if weechat.config_get_plugin('debug') == "on":
        print "data: " + data
        print "signal: " + signal
        print "message: " + signal_data
        print "buffer: " + buffer

    # Create an object that will proxy for a particular remote object.
    bus = dbus.SessionBus()
    remote_object = bus.get_object(DBUS_CONNECTION, DBUS_OBJ_PATH)
    remote_object.del_messages(buffer)

    return weechat.WEECHAT_RC_OK

##### END FUNCTIONS #####

settings = {
    'show_hilights' : ('on', 'Should hilights trigger indications' ),
    'show_priv_msg' : ('on', 'Should privmsgs trigger indications' ),
}

if weechat.register(SCRIPT_NAME,
                    SCRIPT_AUTHOR,
                    SCRIPT_VERSION,
                    SCRIPT_LICENSE,
                    SCRIPT_DESC,
                    "weechat_script_end",
                    ""):
    version = weechat.info_get('version_number', '') or 0

    # Init everything
    for option, default_desc in settings.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_desc[0])
        if int(version) >= 0x00030500:
            weechat.config_set_desc_plugin(option, default_desc[1])

    # Perform some sanity checks to make sure we have everything we need to run
    sanity = True
    weechat_windowid = os.environ.get('WINDOWID')
    if weechat_windowid == None:
        weechat.prnt("", "%sEnvironment variable WINDOWID not set.  This script requires an X environment to run." % weechat.prefix("error"))
        sanity = False

    fifo_filename = weechat.info_get("fifo_filename", "")
    if fifo_filename == "":
        weechat.prnt("", "%sWeechat variable fifo_filename is not set.  Is the fifo plugin enabled?" % weechat.prefix("error"))
        sanity = False

    if sanity:
        Subprocess.start(fifo_filename, weechat_windowid)

        # Hook privmsg/hilights
        weechat.hook_print("", "", "", 1, "notify_msg", "")
        weechat.hook_signal("buffer_switch", "buffer_switched", "")
