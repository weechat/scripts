#
# Copyright (C) 2014 Guido Berhoerster <guido+weechat@berhoerster.name>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import time
import re
import select
import signal
import errno
import fcntl
import cgi
import multiprocessing


SCRIPT_NAME = 'notification'
APPLICATION = 'Weechat'
VERSION = '1'
AUTHOR = 'Guido Berhoerster'
COPYRIGHT = '(C) 2014 Guido Berhoerster'
SUBTITLE = 'Notification Plugin for Weechat'
HOMEPAGE = 'https://code.guido-berhoerster.org/addons/weechat-scripts/weechat-notification-script/'
EMAIL = 'guido+weechat@berhoerster.name'
DESCRIPTION = 'Notifies of a number of events through desktop notifications ' \
        'and an optional status icon'
DEFAULT_SETTINGS = {
    'status_icon': ('weechat', 'path or name of the status icon'),
    'notification_icon': ('weechat', 'path or name of the icon shown in '
            'notifications'),
    'preferred_toolkit': ('', 'preferred UI toolkit'),
    'notify_on_displayed_only': ('on', 'only notify of messages that are '
            'actually displayed'),
    'notify_on_privmsg': ('on', 'notify when receiving a private message'),
    'notify_on_highlight': ('on', 'notify when a messages is highlighted'),
    'notify_on_dcc_request': ('on', 'notify on DCC requests')
}
BUFFER_SIZE = 1024


class NetstringParser(object):
    """Netstring Stream Parser"""

    IN_LENGTH = 0
    IN_STRING = 1

    def __init__(self, on_string_complete):
        self.on_string_complete = on_string_complete
        self.length = 0
        self.input_buffer = ''
        self.state = self.IN_LENGTH

    def parse(self, data):
        self.input_buffer += data
        ret = True
        while ret:
            if self.state == self.IN_LENGTH:
                ret = self.parse_length()
            else:
                ret = self.parse_string()

    def parse_length(self):
        length, delimiter, self.input_buffer = self.input_buffer.partition(':')
        if not delimiter:
            return False
        try:
            self.length = int(length)
        except ValueError:
            raise SyntaxError('Invalid length: %s' % length)
        self.state = self.IN_STRING
        return True

    def parse_string(self):
        input_buffer_len = len(self.input_buffer)
        if input_buffer_len < self.length + 1:
            return False
        string = self.input_buffer[0:self.length]
        if self.input_buffer[self.length] != ',':
            raise SyntaxError('Missing delimiter')
        self.input_buffer = self.input_buffer[self.length + 1:]
        self.length = 0
        self.state = self.IN_LENGTH
        self.on_string_complete(string)
        return True


def netstring_encode(*args):
    return ''.join(['%d:%s,' % (len(element), element) for element in
            args])

def netstring_decode(netstring):
    result = []
    def append_result(data):
        result.append(data)
    np = NetstringParser(append_result)
    np.parse(netstring)
    return result

def dispatch_weechat_callback(*args):
    return weechat_callbacks[args[0]](*args)

def create_weechat_callback(method):
    global weechat_callbacks

    method_id = str(id(method))
    weechat_callbacks[method_id] = method
    return method_id


class Notifier(object):
    """Simple notifier which discards all notifications, base class for all
       other notifiers
    """

    def __init__(self, icon):
        flags = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        self.parser = NetstringParser(self.on_command_received)

    def on_command_received(self, raw_command):
        command_args = netstring_decode(raw_command)
        if len(command_args) > 1:
            command = command_args[0]
            args = netstring_decode(command_args[1])
        else:
            command = command_args[0]
            args = []
        getattr(self, command)(*args)

    def notify(self, summary, message, icon):
        pass

    def reset(self):
        pass

    def run(self):
        poll = select.poll()
        poll.register(sys.stdin, select.POLLIN | select.POLLPRI)

        while True:
            try:
                events = poll.poll()
            except select.error as e:
                if e.args and e.args[0] == errno.EINTR:
                    continue
                else:
                    raise e
            for fd, event in events:
                if event & (select.POLLIN | select.POLLPRI):
                    buffer_ = os.read(fd, BUFFER_SIZE)
                    if buffer_ != '':
                        self.parser.parse(buffer_)
                if event & (select.POLLERR | select.POLLHUP | select.POLLNVAL):
                    sys.exit(1)


class Gtk2Notifier(Notifier):
    """GTK 2 notifier based on pygtk and pynotify"""

    def __init__(self, icon):
        super(Gtk2Notifier, self).__init__(icon)

        pynotify.init(APPLICATION)

        gobject.io_add_watch(sys.stdin, gobject.IO_IN | gobject.IO_PRI,
                self.on_input)

        if not icon:
            icon_name = None
            icon_pixbuf = None
        elif icon.startswith('/'):
            icon_name = None
            try:
                icon_pixbuf = gtk.gdk.Pixbuf.new_from_file(icon)
            except gobject.GError:
                icon_pixbuf = None
        else:
            icon_name = icon
            icon_pixbuf = None

        if icon_name or icon_pixbuf:
            self.status_icon = gtk.StatusIcon()
            self.status_icon.set_title(APPLICATION)
            self.status_icon.set_tooltip_text(APPLICATION)
            self.status_icon.connect('activate', self.on_activate)
            if icon_name:
                self.status_icon.set_from_icon_name(icon_name)
            elif icon_pixbuf:
                self.status_icon.set_from_pixbuf(icon_pixbuf)
        else:
            self.status_icon = None

    def on_input(self, fd, cond):
        if cond & (gobject.IO_IN | gobject.IO_PRI):
            try:
                buffer_ = os.read(fd.fileno(), BUFFER_SIZE)
                if buffer_ != '':
                    self.parser.parse(buffer_)
            except EOFError:
                gtk.main_quit()
                return False

        if cond & (gobject.IO_ERR | gobject.IO_HUP):
            gtk.main_quit()
            return False

        return True

    def on_activate(self, widget):
        self.reset()

    def on_notification_closed(self, notification):
        if notification.get_closed_reason() == 2:
            self.reset()

    def notify(self, summary, message, icon):
        if self.status_icon:
            self.status_icon.set_tooltip_text('%s: %s' % (APPLICATION,
                    summary))
            self.status_icon.set_blinking(True)

        if icon and icon.startswith('/'):
            icon_name = None
            try:
                icon_pixbuf = gtk.gdk.Pixbuf.new_from_file(icon)
            except gobject.GError:
                icon_pixbuf = None
        else:
            icon_name = icon
            icon_pixbuf = None

        if 'body-markup' in pynotify.get_server_caps():
            body = cgi.escape(message)
        else:
            body = message

        notification = pynotify.Notification(summary, body, icon_name)
        if icon_pixbuf is not None:
            notification.set_image_from_pixbuf(icon_pixbuf)
        notification.connect('closed', self.on_notification_closed)
        notification.show()

    def reset(self):
        if self.status_icon:
            self.status_icon.set_tooltip_text(APPLICATION)
            self.status_icon.set_blinking(False)

    def run(self):
        gtk.main()


class Gtk3Notifier(Notifier):
    """GTK3 notifier based on GObject Introspection Bindings for GTK 3 and
       libnotify
    """

    def __init__(self, icon):
        super(Gtk3Notifier, self).__init__(icon)

        Notify.init(APPLICATION)

        GLib.io_add_watch(sys.stdin, GLib.IO_IN | GLib.IO_PRI, self.on_input)

        if not icon:
            self.icon_name = None
            self.icon_pixbuf = None
        elif icon.startswith('/'):
            self.icon_name = None
            try:
                self.icon_pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon)
            except GLib.GError:
                self.icon_pixbuf = None
        else:
            self.icon_name = icon
            self.icon_pixbuf = None

        if self.icon_name or self.icon_pixbuf:
            # create blank, fully transparent pixbuf in order to simulate
            # blinking
            self.blank_pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,
                    True, 8, 22, 22)
            self.blank_pixbuf.fill(0x00)

            self.blink_on = True
            self.blink_timeout_id = None

            self.status_icon = Gtk.StatusIcon.new()
            self.status_icon.set_title(APPLICATION)
            self.status_icon.set_tooltip_text(APPLICATION)
            self.status_icon.connect('activate', self.on_activate)
            self.update_icon()
        else:
            self.status_icon = None

    def on_input(self, fd, cond):
        if cond & (GLib.IO_IN | GLib.IO_PRI):
            try:
                self.parser.parse(os.read(fd.fileno(), BUFFER_SIZE))
            except EOFError:
                Gtk.main_quit()
                return False

        if cond & (GLib.IO_ERR | GLib.IO_HUP):
            Gtk.main_quit()
            return False

        return True

    def on_activate(self, widget):
        self.reset()

    def update_icon(self):
        if not self.blink_on:
            self.status_icon.set_from_pixbuf(self.blank_pixbuf)
        elif self.icon_name:
            self.status_icon.set_from_icon_name(self.icon_name)
        elif self.icon_pixbuf:
            self.status_icon.set_from_pixbuf(self.icon_pixbuf)

    def on_blink_timeout(self):
        self.blink_on = not self.blink_on
        self.update_icon()
        return True

    def on_notification_closed(self, notification):
        if notification.get_closed_reason() == 2:
            self.reset()

    def notify(self, summary, message, icon):
        if self.status_icon:
            self.status_icon.set_tooltip_text('%s: %s' % (APPLICATION,
                    summary))
            if self.blink_timeout_id is None:
                self.blink_timeout_id = GLib.timeout_add(500,
                        self.on_blink_timeout)

        if icon and icon.startswith('/'):
            icon_name = None
            try:
                icon_pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon)
            except GLib.GError:
                icon_pixbuf = None
        else:
            icon_name = icon
            icon_pixbuf = None

        if 'body-markup' in Notify.get_server_caps():
            body = cgi.escape(message)
        else:
            body = message

        notification = Notify.Notification.new(summary, body, icon_name)
        if icon_pixbuf is not None:
            notification.set_image_from_pixbuf(icon_pixbuf)
        notification.connect('closed', self.on_notification_closed)
        notification.show()

    def reset(self):
        if self.status_icon:
            self.status_icon.set_tooltip_text(APPLICATION)
            if self.blink_timeout_id is not None:
                GLib.source_remove(self.blink_timeout_id)
                self.blink_timeout_id = None
                self.blink_on = True
                self.update_icon()

    def run(self):
        Gtk.main()


class Qt4Notifier(Notifier):
    """Qt 4 notifier"""

    def __init__(self, icon):
        super(Qt4Notifier, self).__init__(icon)

        signal.signal(signal.SIGINT, self.on_sigint)

        self.qapplication = QtGui.QApplication([])

        self.readable_notifier = QtCore.QSocketNotifier(sys.stdin.fileno(),
                QtCore.QSocketNotifier.Read)
        self.readable_notifier.activated.connect(self.on_input)
        self.readable_notifier.setEnabled(True)

        if not icon:
            self.icon = None
        elif icon.startswith('/'):
            self.icon = QtGui.QIcon(icon)
        else:
            self.icon = QtGui.QIcon.fromTheme(icon)

        if self.icon:
            # create blank, fully transparent pixbuf in order to simulate
            # blinking
            self.blank_icon = QtGui.QIcon()

            self.blink_on = True
            self.blinking_timer = QtCore.QTimer()
            self.blinking_timer.setInterval(500)
            self.blinking_timer.timeout.connect(self.on_blink_timeout)

            self.status_icon = QtGui.QSystemTrayIcon()
            self.status_icon.setToolTip(APPLICATION)
            self.update_icon()
            self.status_icon.setVisible(True)
            self.status_icon.activated.connect(self.on_activated)
            self.status_icon.messageClicked.connect(self.on_message_clicked)
        else:
            self.status_icon = None

    def on_sigint(self, signo, frame):
        self.qapplication.exit(0)

    def on_input(self, fd):
        try:
            self.parser.parse(os.read(fd, BUFFER_SIZE))
        except EOFError:
            self.qapplication.exit(1)

    def on_activated(self, reason):
        self.reset()

    def on_message_clicked(self):
        self.reset()

    def on_blink_timeout(self):
        self.blink_on = not self.blink_on
        self.update_icon()

    def update_icon(self):
        if not self.blink_on:
            self.status_icon.setIcon(self.blank_icon)
        else:
            self.status_icon.setIcon(self.icon)

    def notify(self, summary, message, icon):
        if self.status_icon:
            self.status_icon.setToolTip('%s: %s' % (APPLICATION,
                    cgi.escape(summary)))
            self.blinking_timer.start()
            if self.status_icon.supportsMessages():
                self.status_icon.showMessage(summary, message,
                        QtGui.QSystemTrayIcon.NoIcon)

    def reset(self):
        if self.status_icon:
            self.blinking_timer.stop()
            self.blink_on = True
            self.update_icon()
            self.status_icon.setToolTip(APPLICATION)

    def run(self):
        sys.exit(self.qapplication.exec_())


class KDE4Notifier(Notifier):
    """KDE 4 notifier based on PyKDE4"""

    def __init__(self, icon):
        super(KDE4Notifier, self).__init__(icon)

        signal.signal(signal.SIGINT, self.on_sigint)

        aboutData = kdecore.KAboutData(APPLICATION.lower(), '',
                kdecore.ki18n(APPLICATION), VERSION, kdecore.ki18n(SUBTITLE),
                kdecore.KAboutData.License_GPL_V3, kdecore.ki18n(COPYRIGHT),
                kdecore.ki18n (''), HOMEPAGE, EMAIL)
        kdecore.KCmdLineArgs.init(aboutData)
        self.kapplication = kdeui.KApplication()

        self.readable_notifier = QtCore.QSocketNotifier(sys.stdin.fileno(),
                QtCore.QSocketNotifier.Read)
        self.readable_notifier.activated.connect(self.on_input)
        self.readable_notifier.setEnabled(True)

        if not icon:
            icon_qicon = None
            icon_name = None
        elif icon.startswith('/'):
            icon_qicon = QtGui.QIcon(icon)
            icon_name = None
        else:
            icon_qicon = None
            icon_name = icon

        if icon_name or icon_pixmap:
            self.status_notifier = kdeui.KStatusNotifierItem(self.kapplication)
            self.status_notifier.setCategory(
                    kdeui.KStatusNotifierItem.Communications)
            if icon_name:
                self.status_notifier.setIconByName(icon_name)
                self.status_notifier.setToolTip(icon_name, APPLICATION,
                        SUBTITLE)
            else:
                self.status_notifier.setIconByPixmap(icon_qicon)
                self.status_notifier.setToolTip(icon_qicon, APPLICATION,
                        SUBTITLE)
            self.status_notifier.setStandardActionsEnabled(False)
            self.status_notifier.setStatus(kdeui.KStatusNotifierItem.Active)
            self.status_notifier.setTitle(APPLICATION)
            self.status_notifier.activateRequested.connect(
                    self.on_activate_requested)
        else:
            self.status_notifier = None

    def on_sigint(self, signo, frame):
        self.kapplication.exit(0)

    def on_input(self, fd):
        try:
            self.parser.parse(os.read(fd, BUFFER_SIZE))
        except EOFError:
            self.kapplication.exit(1)

    def on_activate_requested(self, active, pos):
        self.reset()

    def notify(self, summary, message, icon):
        if self.status_notifier:
            self.status_notifier.setToolTipSubTitle(cgi.escape(summary))
            self.status_notifier.setStatus(
                    kdeui.KStatusNotifierItem.NeedsAttention)

        if icon:
            if icon.startswith('/'):
                pixmap = QtGui.QPixmap.load(icon)
            else:
                pixmap = kdeui.KIcon(icon).pixmap(kdeui.KIconLoader.SizeHuge,
                        kdeui.KIconLoader.SizeHuge)
        else:
            pixmap = QtGui.QPixmap()
        kdeui.KNotification.event(kdeui.KNotification.Notification, summary,
                cgi.escape(message), pixmap)

    def reset(self):
        if self.status_notifier:
            self.status_notifier.setStatus(kdeui.KStatusNotifierItem.Active)
            self.status_notifier.setToolTipTitle(APPLICATION)
            self.status_notifier.setToolTipSubTitle(SUBTITLE)

    def run(self):
        sys.exit(self.kapplication.exec_())


class NotificationProxy(object):
    """Proxy object for interfacing with the notifier process"""

    def __init__(self, preferred_toolkit, status_icon):
        self.script_file = os.path.realpath(__file__)
        self._status_icon = status_icon
        self._preferred_toolkit = preferred_toolkit
        self.notifier_process_hook = None
        self.spawn_timer_hook = None
        self.next_spawn_time = 0.0

        self.spawn_notifier_process()

    @property
    def status_icon(self):
        return self._status_icon

    @status_icon.setter
    def status_icon(self, value):
        self._status_icon = value
        self.terminate_notifier_process()
        self.spawn_notifier_process()

    @property
    def preferred_toolkit(self):
        return self._preferred_toolkit

    @preferred_toolkit.setter
    def preferred_toolkit(self, value):
        self._preferred_toolkit = value
        self.terminate_notifier_process()
        self.spawn_notifier_process()

    def on_notifier_process_event(self, data, command, return_code, output,
            error_output):
        if return_code != weechat.WEECHAT_HOOK_PROCESS_RUNNING:
            if return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
                error = '%sfailed to run notifier' % weechat.prefix("error")
            else:
                error = '%snotifier exited with exit status %d' % \
                        (weechat.prefix("error"), return_code)
            if output:
                error += '\nstdout:%s' % output
            if error_output:
                error += '\nstderr:%s' % error_output
            weechat.prnt('', error)
            self.notifier_process_hook = None
            self.spawn_notifier_process()
        return weechat.WEECHAT_RC_OK

    def on_spawn_timer(self, data, remaining):
        self.spawn_timer_hook = None
        if not self.notifier_process_hook:
            self.spawn_notifier_process()
        return weechat.WEECHAT_RC_OK

    def spawn_notifier_process(self):
        if self.notifier_process_hook or self.spawn_timer_hook:
            return

        # do not try to respawn a notifier more than once every ten seconds
        now = time.time()
        if long(self.next_spawn_time - now) > 0:
            self.spawn_timer_hook = \
                    weechat.hook_timer(long((self.next_spawn_time - now) *
                    1000), 0, 1, 'dispatch_weechat_callback',
                    create_weechat_callback(self.on_spawn_timer))
            return

        self.next_spawn_time = now + 10
        self.notifier_process_hook = \
                weechat.hook_process_hashtable(sys.executable, {'arg1':
                self.script_file, 'arg2': self.preferred_toolkit, 'arg3':
                self.status_icon, 'stdin': '1'}, 0,
                'dispatch_weechat_callback',
                create_weechat_callback(self.on_notifier_process_event))

    def terminate_notifier_process(self):
        if self.spawn_timer_hook:
            weechat.unhook(self.spawn_timer_hook)
            self.spawn_timer_hook = None
        if self.notifier_process_hook:
            weechat.unhook(self.notifier_process_hook)
            self.notifier_process_hook = None
        self.next_spawn_time = 0.0

    def send(self, command, *args):
        if self.notifier_process_hook:
            if args:
                weechat.hook_set(self.notifier_process_hook, 'stdin',
                        netstring_encode(netstring_encode(command,
                        netstring_encode(*args))))
            else:
                weechat.hook_set(self.notifier_process_hook, 'stdin',
                        netstring_encode(netstring_encode(command)))

    def notify(self, summary, message, icon):
        self.send('notify', summary, message, icon)

    def reset(self):
        self.send('reset')


class NotificationPlugin(object):
    """Weechat plugin"""

    def __init__(self):
        self.DCC_SEND_RE = re.compile(r':(?P<sender>\S+) PRIVMSG \S+ :'
                r'\x01DCC SEND (?P<filename>\S+) \d+ \d+ (?P<size>\d+)')
        self.DCC_CHAT_RE = re.compile(r':(?P<sender>\S+) PRIVMSG \S+ :'
                r'\x01DCC CHAT ')

        weechat.register(SCRIPT_NAME, AUTHOR, VERSION, 'GPL3', DESCRIPTION, '',
                '')

        for option, (value, description) in DEFAULT_SETTINGS.iteritems():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, value)
            weechat.config_set_desc_plugin(option, '%s (default: "%s")' %
                    (description, value))

        self.notification_proxy = NotificationProxy(
            weechat.config_get_plugin('preferred_toolkit'),
            weechat.config_get_plugin('status_icon'))

        weechat.hook_print('', 'irc_privmsg', '', 1,
                'dispatch_weechat_callback',
                create_weechat_callback(self.on_message))
        weechat.hook_signal('key_pressed', 'dispatch_weechat_callback',
                create_weechat_callback(self.on_key_pressed))
        weechat.hook_signal('irc_dcc', 'dispatch_weechat_callback',
                create_weechat_callback(self.on_dcc))
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME,
                'dispatch_weechat_callback',
                create_weechat_callback(self.on_config_changed))

    def on_message(self, data, buffer, date, tags, displayed, highlight,
            prefix, message):
        if weechat.config_get_plugin('notify_on_displayed_only') == 'on' and \
                int(displayed) != 1:
            return weechat.WEECHAT_RC_OK

        formatted_date = time.strftime('%H:%M', time.localtime(float(date)))
        if 'notify_private' in tags.split(',') and \
                weechat.config_get_plugin('notify_on_privmsg') == 'on':
            summary = 'Private message from %s at %s' % (prefix,
                    formatted_date)
            self.notification_proxy.notify(summary, message,
                    weechat.config_get_plugin('notification_icon'))
        elif int(highlight) == 1 and \
                weechat.config_get_plugin('notify_on_highlight') == 'on':
            summary = 'Highlighted message from %s at %s' % (prefix,
                    formatted_date)
            self.notification_proxy.notify(summary, message,
                    weechat.config_get_plugin('notification_icon'))

        return weechat.WEECHAT_RC_OK

    def on_dcc(self, data, signal, signal_data):
        if weechat.config_get_plugin('notify_on_dcc') != 'on':
            return weechat.WEECHAT_RC_OK

        matches = self.DCC_SEND_RE.match(signal_data)
        if matches:
            summary = 'DCC send request from %s' % matches.group('sender')
            message = 'Filname: %s, Size: %d bytes' % \
                    (matches.group('filename'), int(matches.group('size')))
            self.notification_proxy.notify(summary, message,
                    weechat.config_get_plugin('notification_icon'))
            return weechat.WEECHAT_RC_OK

        matches = self.DCC_CHAT_RE.match(signal_data)
        if matches:
            summary = 'DCC chat request from %s' % matches.group('sender')
            message = ''
            self.notification_proxy.notify(summary, message,
                    weechat.config_get_plugin('notification_icon'))
            return weechat.WEECHAT_RC_OK

        return weechat.WEECHAT_RC_OK

    def on_key_pressed(self, data, signal, signal_data):
        self.notification_proxy.reset()
        return weechat.WEECHAT_RC_OK

    def on_config_changed(self, data, option, value):
        if option.endswith('.preferred_toolkit'):
            self.notification_proxy.preferred_toolkit = value
        elif option.endswith('.status_icon'):
            self.notification_proxy.status_icon = value
        return weechat.WEECHAT_RC_OK


def import_modules(modules):
    for module_name, fromlist in modules:
        if fromlist:
            module = __import__(module_name, fromlist=fromlist)
            for identifier in fromlist:
                globals()[identifier] = getattr(module, identifier)
        else:
            globals()[module_name] = __import__(module_name)

def try_import_modules(modules):
    try:
        import_modules(modules)
    except ImportError:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    if sys.argv[0] == '__weechat_plugin__':
        # running as Weechat plugin
        import weechat

        weechat_callbacks = {}

        plugin = NotificationPlugin()
    elif len(sys.argv) == 3:
        # running as the notifier process
        preferred_toolkit = sys.argv[1]
        icon = sys.argv[2]

        # required modules for each toolkit
        toolkits_modules = {
            'gtk3': [
                ('gi.repository', [
                    'GLib',
                    'GdkPixbuf',
                    'Gtk',
                    'Notify'
                ])
            ],
            'gtk2': [
                ('pygtk', []),
                ('gobject', []),
                ('gtk', []),
                ('pynotify', [])
            ],
            'qt4': [
                ('PyQt4', [
                    'QtGui',
                    'QtCore'
                ])
            ],
            'kde4': [
                ('PyQt4', [
                    'QtGui',
                    'QtCore'
                ]),
                ('PyKDE4', [
                    'kdecore',
                    'kdeui'
                ])
            ],
            '': []
        }
        available_toolkits = []
        selected_toolkit = ''

        # find available toolkits by spawning a process for each toolkit which
        # tries to import all required modules and returns an exit status of 1
        # in case of an import error
        for toolkit in toolkits_modules:
            process = multiprocessing.Process(target=try_import_modules,
                    args=(toolkits_modules[toolkit],))
            process.start()
            process.join(3)
            if process.is_alive():
                process.terminate()
                process.join()
            if process.exitcode == 0:
                available_toolkits.append(toolkit)

        # select toolkit based on either explicit preference or the
        # availability of modules and the used desktop environment
        if preferred_toolkit:
            if preferred_toolkit in available_toolkits:
                selected_toolkit = preferred_toolkit
        else:
            if 'KDE_FULL_SESSION' in os.environ:
                # preferred order if running KDE4
                toolkits = ['kde4', 'qt4', 'gtk3', 'gtk2']
            else:
                # preferred order for all other desktop environments
                toolkits = ['gtk3', 'gtk2', 'qt4', 'kde4']
            for toolkit in toolkits:
                if toolkit in available_toolkits:
                    selected_toolkit = toolkit
                    break

        # import required toolkit modules
        import_modules(toolkits_modules[selected_toolkit])

        # run selected notifier
        if selected_toolkit == 'gtk3':
            notifier = Gtk3Notifier(icon)
        elif selected_toolkit == 'gtk2':
            notifier = Gtk2Notifier(icon)
        elif selected_toolkit == 'qt4':
            notifier = Qt4Notifier(icon)
        elif selected_toolkit == 'kde4':
            notifier = KDE4Notifier(icon)
        else:
            notifier = Notifier(icon)
        notifier.run()
    else:
        sys.exit(1)
