# Author: Leon Bogaert <leon AT tim-online DOT nl>
# This Plugin Calls the libindicate bindings via python when somebody says your
# nickname, sends you a query, etc.
# To make it work, you may need to download: python-indicate and python-dbus
# Requires Weechat 0.3.0
# Released under GNU GPL v2
#
# 2010-09-22, Leon <leon@tim-online.nl>:
#     version 0.0.1 Intial release
# 
# @TODO: find out how to jump to buffer/line
# @TODO: how to communicate the click to weechat
# @TODO: decide what to do if a user clicks an indicator an then start typing:
#        * leave indicators alone
#        * remove indicators in the "neighbourhood"
#        * If a user cliks indicator: indactor dissapears
#        * On click group: remove all indicators
#        * When visiting buffer: remove indicators

import dbus.service
import inspect
import os
import tempfile

class DBUSService(dbus.service.Object):
    def __init__(self, messageMenu):
        bus_name = dbus.service.BusName('org.weechat.scripts.windicate', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/org/weechat/scripts/windicate')
        self.messageMenu = messageMenu
 
    @dbus.service.method('org.weechat.scripts.windicate')
    def add_message(self, channel, sender, body):
        return self.messageMenu.add_message(channel, sender, body)

class MessageMenu(object):
    def __init__(self):
        self.messages = []

        server = pyindicate.indicate_server_ref_default()
        server.set_type("message.im")
        server.set_desktop_file(self.desktop_file())
        server.connect("server-display", self.server_click)
        server.show()

    def desktop_file(self):
        file = "/usr/share/applications/weechat.desktop"

        if os.path.isfile(file):
            return file

        f = tempfile.NamedTemporaryFile(suffix='indicator', delete=False)
        f.write("[Desktop Entry]\nEncoding=UTF-8\nMultipleArgs=false\nTerminal=true\nExec=weechat-curses\nIcon=weechat\nType=Application\nCategories=Network;IRCClient;\nStartupNotify=false\nName=Weechat\nGenericName=IRC Client")
        f.close()
        self.tmp_file = f

        return f.name

    def __del__(self):
        if self.tmp_file and os.file.exists(self.tmp_file):
            os.unlink(self.tmp_file)

    def server_click(self, server, time):
        print "Server clicked!"

    def add_message(self, channel, sender, body):
        for message in self.messages:
            if message.channel == channel and message.sender == sender:
                return message.update_time()

        return self.messages.append(Message(self, channel, sender, body))

class Message(object):
    def __init__(self, mm, channel, sender, message):
        # Setup the message
        try:
            # Ubuntu 9.10 and above
            indicator = pyindicate.Indicator()
        except:
            # Ubuntu 9.04
            indicator = pyindicate.IndicatorMessage()

        indicator.set_property("subtype", "im")
        indicator.set_property("sender", "%s (%s)" % (sender, channel))
        indicator.set_property("body", message)
        indicator.set_property_time("time", time())
        indicator.set_property('draw-attention', 'true');
        indicator.show()
        indicator.connect("user-display", self.message_clicked)

        self.indicator = indicator
        self.sender = sender
        self.message = message
        self.channel = channel
        self.messageMenu = mm

    def update_time(self):
        self.indicator.set_property_time("time", time())
        
    def message_clicked(self, indicator, time):
        #How can I make weechat go there?? (/buffer self.channeli)
        #Maybe if I can get dbus running in a weechat script...
        self.messageMenu.messages.remove(self)
        indicator.hide()

class WindicateServer(object):
    def __init__(self):
        DBusGMainLoop(set_as_default=True)
        mm = MessageMenu()
        dbs = DBUSService(mm)

        loop = gobject.MainLoop()
        loop.run()

class Subprocess(object):
    p = None

    @classmethod
    def start(cls):
        file = inspect.getfile( inspect.currentframe())

        import subprocess
        args = ["/usr/bin/python", file]
        cls.p = subprocess.Popen(args)

    @classmethod
    def stop(cls):
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
    ws = WindicateServer()

##### FUNCTIONS #####
def windicate_server_ended(data, command, rc, stdout, stderr):
    print "windicate_server_ended"
    return weechat.WEECHAT_RC_OK

def weechat_script_end():
    Subprocess.stop()
    return weechat.WEECHAT_RC_OK

def notify_msg(data, bufferp, time, tags, display, is_hilight, prefix, msg):
    """Sends highlighted message to be printed on notification"""

    if ('notify_private' in tags and 
        weechat.config_get_plugin('show_priv_msg') == "on") \
        or (is_hilight == "1" and \
        weechat.config_get_plugin('show_hilights') == "on"):

        if not weechat.buffer_get_string(bufferp, "short_name"):
            buffer = weechat.buffer_get_string(bufferp, "name")
        else:
            buffer = weechat.buffer_get_string(bufferp, "short_name")

        if ('notify_private' in tags):
            buffer = "private"

        add_message(buffer, prefix, msg)

        if weechat.config_get_plugin('debug') == "on":
            print prefix

    return weechat.WEECHAT_RC_OK

def notify_show_hi(data, signal, message):
    print "data: " + data
    print "signal: " + data
    print "message: " + message
    return weechat.WEECHAT_RC_OK

def notify_show_priv(data, signal, message):
    print "data: " + data
    print "signal: " + data
    print "message: " + message
    return weechat.WEECHAT_RC_OK

def add_message(channel, sender, body):
    bus = dbus.SessionBus()

    # Create an object that will proxy for a particular remote object.
    remote_object = bus.get_object("org.weechat.scripts.windicate", # Connection name
                                   "/org/weechat/scripts/windicate" # Object's path
                                  )
    remote_object.add_message(channel, sender, body)
##### END FUNCTIONS #####

weechat.register("windicate", "Leon Bogaert", "0.0.1", "GPL",
                 "fills the indicate applet", "weechat_script_end", "")

# script options
settings = {
    "show_hilights" : "on",
    "show_priv_msg" : "on",
    "time_between_msg" : "5",
}

# Init everything
for option, default_value in settings.items():
    if weechat.config_get_plugin(option) == "":
        weechat.config_set_plugin(option, default_value)

Subprocess.start()

#weechat.hook_process("/usr/bin/python %s" % (file,),
                     #-1, "windicate_server_ended", "")

# Hook privmsg/hilights
weechat.hook_print("", "", "", 1, "notify_msg", "")
#weechat.hook_signal("weechat_highlight", "notify_show_hi", "")
#weechat.hook_signal("weechat_pv", "notify_show_priv", "")
