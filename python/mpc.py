"""
:Author: P Hargrave <resixianatgmaildotcom>

:What it does:
Allows control of an mpd server from within weechat.

Also provides the 'now playing' (np) command to publish
currently playing track information into the current buffer.

:Usage:
    /mpc

    * When called with no command 'np' is assumed

    /mpc <command> <arg1 arg2 ...>

    *Arguments may be comma or space separated.

:Configuration:
==============|==========================================
Variable name | Description [Default Value]
==============|==========================================

format.........This is a string that will be used to show
               the 'now playing' banner.
               Use `$` to precede any variable name.

               Several keys are already avaialable just
               from the mpd.MPDClient() `currentsong`
               command. (So set verbose=1 then do a
               `mpc currentsong` to see all the keys)

               As a convenience the following are also
               available:
                $title_or_file,
                $length_min, $length_sec, $pct,
                $pos_min, $pos_sec,
                $bitrate

host...........The host where your mpd runs ["localhost"]
password.......The password used to connect to mpd [""]
port...........The port to connect to mpd (usually 6600)
verbose........If set then lots more will be printed
ch_pause.......These are just inserted in the short_status
ch_play        template displayed whenever an action is
ch_stop        performed.
autoswitch.....If set automatically switch to created
               buffers (e.g. playlist)

To restore the default value of any config variable just
/unset <the_variable> and reload the plugin.

:Requires:
 python-mpd: Python MPD client library
             http://mpd.wikia.com/wiki/ClientLib:python-mpd

:Etc...:
This script was originally devised while hacking mpdnp.py
script by Henning Hasemann. Since there is basically nothing
left of the original and all the controls are new I decided
'mpc' was more appropriate now.

All the commands are those available from the mpd.py MPDClient
object, mostly I have done little to wrap these for weechat,
but a few common ones can show some basic information in the
current buffer (e.g. when you pause/play/stop). Unfortunately
these functions are not documented afaik and so I can't even
be sure of the arguments or types, so the user may need to
do some experimenting ;)

Released under GPL license.

2013-01-03, Sebastien Helleu <flashcode@flashtux.org>:
    version 0.3: fix buffer used to print message (use buffer in command
                 callback, not current buffer)
"""

import weechat as wc
from mpd import MPDClient, CommandError
from string import Template
from os.path import basename, splitext
from operator import itemgetter

DEFAULT_FMT = \
    "/me is listening to: $artist - $title_or_file ($length_min:$length_sec)"

wc.register("mpc", "Perry Hargrave", "0.3", "GPL", "mpc for weechat", "", "")

DEFAULT_CONFIG = {
    "host"      : "localhost",
    "port"      : "6600",
    "format"    : DEFAULT_FMT,
    "password"  : "",
    "verbose"   : "1",
    "debug"     : "0",
    "ch_pause"  : "||",
    "ch_play"   : ">>",
    "ch_stop"   : "--",
    "shortstats": "MPC : $state : $artist : $title",
    "playinfo"  : "$pos: $artist : $title : $album : $track : $time",
    "autoswitch": "0",
}

class __MPC(object):
    _mpdc   = None
    _host   = DEFAULT_CONFIG['host']
    _port   = DEFAULT_CONFIG['port']
    verbose = bool(int(DEFAULT_CONFIG['verbose']))
    debug   = bool(int(DEFAULT_CONFIG['debug']))

    # Switch automatically to created buffers
    autoswitch = bool(int(DEFAULT_CONFIG['autoswitch']))

    # State symbols
    state_chars = {
            'pause':DEFAULT_CONFIG['ch_pause'],
            'play':DEFAULT_CONFIG['ch_play'],
            'stop':DEFAULT_CONFIG['ch_stop'],
            }

    def __init__(self, wc_buffer=None):
        object.__init__(self)
        self._mpdc = MPDClient()
        self._commands = self._mpdc._commands
        self.wcb = wc_buffer

        self.verbose = bool(int((wc.config_get_plugin("verbose"))))
        self.debug = bool(int((wc.config_get_plugin("debug"))))
        self.autoswitch = bool(int((wc.config_get_plugin("autoswitch"))))

        for k, v in self.state_chars.iteritems():
            self.state_chars[k] = wc.config_get_plugin('ch_' + k)

        self._commands['np'] = None

    @property
    def shortstats(self): return wc.config_get_plugin("shortstats")

    def __getattribute__(self, attr):
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            return self._mpdc.__getattr__(attr)

    def _get_status(self, key):
        return self._mpdc.status()[key]

    def _print_current(f):
        """Do `f`, then prints the short_status in the buffer.
        """
        def pf(self, *args, **kwargs):
            robj = f(self, *args, **kwargs)
            if not self.verbose: return robj

            # Show the status in the current buffer
            csong = self._mpdc.currentsong()
            csong.update({'state':self.state_chars[self._get_status('state')]})
            wc.prnt(self.wcb or wc.current_buffer(),
                    Template(self.shortstats).safe_substitute(csong))
            return robj

        return pf

    def connect(self):
        self._host = wc.config_get_plugin("host")
        self._port = int(wc.config_get_plugin("port"))
        self._mpdc.connect(host=self._host, port=self._port)
        pw = wc.config_get_plugin("password")
        if len(pw) > 0: self._mpdc.password(pw)

        if self.debug: wc.prnt(self.wcb or wc.current_buffer(),
                               'mpc debug: Connected')

    def currentsong(self):
        ds = self._mpdc.currentsong()
        itime = int(ds['time'])
        ipos  = int(ds['pos'])
        pct   = int(100 * (ipos / itime))

        ds.update({
            "title_or_file" : ds['title'] or splitext(basename(ds['file']))[0],
            "pos_sec"       : "%02d" % (ipos / 60),
            "pos_min"       : str(ipos / 60),
            "length_sec"    : "%02d" % (itime % 60),
            "length_min"    : str(itime / 60),
            "pct"           : "%2.0f" % pct,
            "bitrate"       : self._get_status('bitrate') + "kbps",
            })

        return ds

    def np(self):
        """Pushes result of np template substitution to current buffer.
        """
        ds  = self.currentsong()
        if len(ds) == 0:
            wc.prnt(self.wcb or wc.current_buffer(), "MPC: ERROR: mpd is stopped")
            return
        wc.command(self.wcb or wc.current_buffer(),
                   Template(wc.config_get_plugin("format")).safe_substitute(ds))

    @_print_current
    def next(self):
        self._mpdc.next()

    @_print_current
    def pause(self):
        self._mpdc.pause()

    @_print_current
    def play(self, *args):
        self._mpdc.play()

    def playlist(self, *args):
        def ifn( b, s, d): wc.prnt(b, Template(s).safe_substitute(d))
        def cfn(): wc.prnt(None, "mpc closing playlist buffer")
        new_buf = wc.buffer_new('mpc: playlist', "ifn", "", "cfn", "")
        wc.buffer_set(new_buf, "localvar_set_no_log", "1")

        pl = self._mpdc.playlist()
        for line in pl:
            wc.prnt(new_buf, line)

        wc.buffer_set(new_buf, "display", "1")
        return pl

    def playlistinfo(self, sortkey='pos'):
        """Shows playlist information sorted by key
        """
        new_buf = wc.buffer_search("", "mpc: playlist")
        if len(new_buf) == 0:
            new_buf = wc.buffer_new('mpc: playlist', "", "", "", "")

        pl = self._mpdc.playlistinfo()
        try:
            # Numerical sort
            spl = sorted(pl,
                         cmp=lambda x,y: cmp(int(x), int(y)),
                         key=itemgetter(sortkey))
        except ValueError:
            # Alpha sort
            lcmp = lambda x,y: cmp(x.lower(), y.lower())
            spl = sorted(pl,
                         cmp=lambda x,y: cmp(x.lower(), y.lower()),
                         key=itemgetter(sortkey))

        t = Template(wc.config_get_plugin("playinfo"))
        for line in spl:
            wc.prnt(new_buf, t.safe_substitute(line))

        return pl

    @_print_current
    def previous(self):
        self._mpdc.previous()

    def random(self, *args):
        """Toggles randomness if no argument is given.
        """
        if len(args) == 0:
            args = [int(not int(self._get_status('random'))),]

        self._mpdc.random(*args)

    @_print_current
    def stop(self, *args):
        self._mpdc.stop()


def set_config():
    for k, v in DEFAULT_CONFIG.iteritems():
        if not wc.config_get_plugin(k):
            wc.config_set_plugin(k, v)


def control(data, wc_buf, cmd):
    """MPC-like controls from weechat.
    """
    debug = bool(int((wc.config_get_plugin("debug"))))

    if len(cmd) < 1: cmd = 'np'
    mpc = __MPC(wc_buffer=wc_buf)
    mpc.connect()
    cmdlist = cmd.split(' ')
    if len(cmdlist) < 2:
        cmdlist = cmd.split(',')

    try:
        f = mpc.__getattribute__(cmdlist[0])
    except AttributeError:
        wc.prnt(wc_buf, 'MPC: ERROR: Invalid command: %s' %cmdlist[0])
        return wc.WEECHAT_RC_ERROR

    if mpc.debug: wc.prnt(wc_buf, 'mpc debug: f=%s' %f)
    if mpc.debug: wc.prnt(wc_buf, 'mpc debug: cmdlist=%s' %cmdlist[1:])

    # FIXME: catch errors here?
    robj = f(*cmdlist[1:])

    if debug: wc.prnt(wc_buf, 'mpc debug: got: %s' %robj)

    return wc.WEECHAT_RC_OK


set_config()
mpc = __MPC()
CMD_LIST = mpc._commands.keys()
del mpc


wc.hook_command("mpc",
                __doc__,
                control.__doc__,
                '| '.join(CMD_LIST[0:]),
                '|| '.join(CMD_LIST[0:]),
                "control", "")
