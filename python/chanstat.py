# -*- coding: utf-8 -*-
###
# Copyright (c) 2010 by Elián Hanisch <lambdae2@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
###

###
# Shows highest and lowest user count for joined channels,
# and an average (for a period of a month)
#
#
#   Commands:
#   * /chanstat
#     Prints current channel stats, see /help chanstat
#
#
#   Settings:
#   * plugins.var.python.chanstat.path:
#     path where to store stat files, deault '%h/chanstat'
#
#   * plugins.var.python.chanstat.averge_period:
#     Period of time for calculate the average stats. This means the avegare will be calculated with
#     the users present in the last x days. Default is 30 days.
#
#   * plugins.var.python.chanstat.show_peaks:
#     If 'on' it will display a message when there's a user peak in any channel.
#     Valid values: on, off
#
#   * plugins.var.python.chanstat.show_lows:
#     If 'on' it will display a message when there's a user low in any channel.
#     Valid values: on, off
#
#
#   History:
#   2010-06-08
#   version 0.1: initial release.
#
###

SCRIPT_NAME    = "chanstat"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Channel statistics"

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://weechat.flashtux.org/"
    import_ok = False

import time
now = lambda : int(time.time())

time_hour = 3600
time_day  = 86400
time_year = 31536000

### messages
def debug(s, args=(), prefix='', name_suffix='debug', level=1):
    """Debug msg"""
    l = weechat.config_get_plugin('debug')
    if not (l and int(l) >= level): return
    buffer_name = '%s_%s' %(SCRIPT_NAME, name_suffix)
    buffer = weechat.buffer_search('python', buffer_name)
    if not buffer:
        buffer = weechat.buffer_new(buffer_name, '', '', '', '')
        weechat.buffer_set(buffer, 'nicklist', '0')
        weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
    weechat.prnt(buffer, '%s\t%s' %(prefix, s %args))

def error(s, prefix=SCRIPT_NAME, buffer=''):
    """Error msg"""
    prefix = prefix or script_nick
    weechat.prnt(buffer, '%s%s %s' %(weechat.prefix('error'), prefix, s))

def say(s, prefix=None, buffer=''):
    """Normal msg"""
    prefix = prefix or script_nick
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

### config and value validation
boolDict = {'on':True, 'off':False}
def get_config_boolean(config):
    value = weechat.config_get_plugin(config)
    try:
        return boolDict[value]
    except KeyError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is invalid, allowed: 'on', 'off'" %value)
        return boolDict[default]

def get_config_int(config):
    value = weechat.config_get_plugin(config)
    try:
        return int(value)
    except ValueError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is not a number." %value)
        return int(default)

def get_dir(filename):
    import os
    basedir = weechat.config_get_plugin('path').replace('%h', weechat.info_get('weechat_dir', ''))
    if not os.path.isdir(basedir):
        os.makedirs(basedir)
    return os.path.join(basedir, filename.lower())


class CaseInsensibleString(str):
    def __init__(self, s=''):
        self.lowered = s.lower()

    def __eq__(self, s):
        try:
            return self.lowered == s.lower()
        except:
            return False

    def __ne__(self, s):
        return not self == s

    def __hash__(self):
        return hash(self.lowered)

def caseInsensibleKey(k):
    if isinstance(k, str):
        return CaseInsensibleString(k)
    elif isinstance(k, tuple):
        return tuple([ caseInsensibleKey(v) for v in k ])
    return k

class CaseInsensibleDict(dict):
    key = staticmethod(caseInsensibleKey)

    def __setitem__(self, k, v):
        dict.__setitem__(self, self.key(k), v)

    def __getitem__(self, k):
        return dict.__getitem__(self, self.key(k))

    def __delitem__(self, k):
        dict.__delitem__(self, self.key(k))

    def __contains__(self, k):
        return dict.__contains__(self, self.key(k))


class Channel(object):
    def __init__(self, max=None, min=None, max_date=None, min_date=None, avrg_date=None,
            avrg_period=None, average=None, count=0):
        if not max:
            max = count
        if not min:
            min = 0
        if not average:
            average = float(count)
        if not max_date:
            max_date = now()
        if not min_date:
            min_date = now()
        if not avrg_date:
            avrg_date = now()
        if not avrg_period:
            avrg_period = 0
        self.max = max
        self.min = min
        self.max_date = max_date
        self.min_date = min_date
        self.avrg_date = avrg_date
        self.avrg_period = avrg_period
        self.average = average

    def __iter__(self):
        return iter((self.max, self.min, self.max_date, self.min_date, self.avrg_date,
            self.avrg_period, self.average))

    def __str__(self):
        return 'Channel(max=%s, average=%s, min_delta=%s)' %(self.max, self.average, self.min)


class StatLog(object):
    def __init__(self):
        self.writers = CaseInsensibleDict()

    @staticmethod
    def make_log(key):
        return get_dir('%s_%s.cvs' %key)

    def log(self, key, *args):
        if key in self.writers:
            writer = self.writers[key]
        else:
            import csv
            filename = self.make_log(key)
            writer = csv.writer(open(filename, 'ab'))
            self.writers[key] = writer

        writer.writerow(args)

    def get_reader(self, key):
        if key in self.writers:
            del self.writers[key]
        import csv
        return csv.reader(open(self.make_log(key)))

    def close(self):
        self.writers = {}


class ChanStatDB(CaseInsensibleDict):
    def __init__(self):
        self.logger = StatLog()

    def __setitem__(self, key, value):
        if not value:
            return
        debug(' ** stats update for %s', args=key[1])
        _now = now()
        avrg = 0
        if key in self:
            chan = self[key]
            if value > chan.max:
                debug('PEAK, %s: %s', args=(key[1], value))
                chan.max = value
                new_channel_peak(key, value, chan.max_date)
                chan.max_date = _now
            elif (chan.max - value) > chan.min:
                # we save the difference between max and min rather the min absolute value, because
                # the minimum min value for a channel would be 1, and that's isn't interesting.
                min_delta = chan.max - value
                debug('LOW, %s: %s', args=(key[1], value))
                chan.min = min_delta
                new_channel_low(key, value, chan.min_date)
                chan.min_date = _now
            # calculate average aproximation
            diff = _now - chan.avrg_date
            #period = 30 * time_day
            period = get_config_int('average_period') * time_day
            if not period:
                period = time_day
            avrg_period = chan.avrg_period
            avrg_period += diff
            if avrg_period > period:
                avrg_period = period
            if diff > avrg_period // 1000 and diff > 600:
                # calc average after 1000th part of the period (10 min minimum)
                max = period // 100
                if diff > max:
                    # too much time have passed since last check, average will be skewed by current
                    # user count, so we reduce the average period.
                    excess = diff - max
                    debug('avrg period correction %s e:%.4f%%', args=(key[1],
                        excess*100.0/avrg_period))
                    diff = max
                    avrg_period -= excess
                    if avrg_period < diff:
                        avrg_period = diff
                avrg = chan.average
                avrg = (avrg * (avrg_period - diff) + value * diff) / avrg_period
                chan.avrg_date = _now
                chan.avrg_period = avrg_period
                # make sure avrg is between max and 1
                if avrg > chan.max:
                    avrg = chan.max
                elif avrg < 1:
                    avrg = 1
                debug('avrg %s %.2f → %.2f (%.4f%% %.4f)', args=(key[1], chan.average, avrg,
                    diff*100.0/avrg_period, avrg - chan.average))
                chan.average = avrg
        else:
            CaseInsensibleDict.__setitem__(self, key, Channel(count=value))

        #if avrg:
        #    self.logger.log(key, _now, value, avrg)
        #else:
        #    self.logger.log(key, _now, value)

    def initchan(self, key, *args):
        CaseInsensibleDict.__setitem__(self, key, Channel(*args))

    def iterchan(self):
        def generator():
            for key in self.keys():
                chan = self[key]
                row = list(key)
                row.extend(chan)
                yield row

        return generator()

    def keys(self):
        """Returns keys sorted"""
        L = dict.keys(self)
        L.sort()
        return L

    def close(self):
        self.logger.close()

channel_stats = ChanStatDB()


def write_database():
    import csv
    filename = get_dir('peak_data.csv')
    try:
        writer = csv.writer(open(filename, 'wb'))
        writer.writerows(channel_stats.iterchan())
    except IOError:
        error('Failed to write chanstat database in %s' %file)

def load_database():
    import csv
    filename = get_dir('peak_data.csv')
    try:
        reader = csv.reader(open(filename, 'rb'))
    except IOError:
        return
    channel_stats.clear()
    for row in reader:
        key = tuple(row[0:2])
        values = row[2:-1]
        values = map(int, values)
        average = row[-1]
        average = float(average)
        values.append(average)
        channel_stats.initchan(key, *values)

def update_user_count(server=None, channel=None):
    if isinstance(channel, str):
        channel = set((channel, ))
    elif channel:
        channel = set(channel)

    def update_channel(server, channel=None):
        channel_infolist = weechat.infolist_get('irc_channel', '', server)
        while weechat.infolist_next(channel_infolist):
            _channel = weechat.infolist_string(channel_infolist, 'name')
            if channel:
                _channel = caseInsensibleKey(_channel)
                if _channel not in channel:
                    continue
            channel_stats[server, _channel] = weechat.infolist_integer(channel_infolist, 'nicks_count')
        weechat.infolist_free(channel_infolist)

    if not server:
        server_infolist = weechat.infolist_get('irc_server', '', '')
        while weechat.infolist_next(server_infolist):
            server = weechat.infolist_string(server_infolist, 'name')
            update_channel(server)
        weechat.infolist_free(server_infolist)
    else:
        update_channel(server, channel)

def time_elapsed(elapsed, ret=None, level=2):
    if ret is None:
        ret = []

    if not elapsed:
        return ''

    if elapsed > time_year:
        years, elapsed = elapsed // time_year, elapsed % time_year
        ret.append('%s%s' %(years, 'y'))
    elif elapsed > time_day:
        days, elapsed = elapsed // time_day, elapsed % time_day
        ret.append('%s%s' %(days, 'd'))
    elif elapsed > time_hour:
        hours, elapsed = elapsed // time_hour, elapsed % time_hour
        ret.append('%s%s' %(hours, 'h'))
    elif elapsed > 60:
        mins, elapsed = elapsed // 60, elapsed % 60
        ret.append('%s%s' %(mins, 'm'))
    else:
        secs, elapsed = elapsed, 0
        ret.append('%s%s' %(secs, 's'))

    if len(ret) >= level or not elapsed:
        return ' '.join(ret)

    ret = time_elapsed(elapsed, ret, level)
    return ret

channel_peak_hooks = CaseInsensibleDict()
msg_queue_timeout = 15
def new_channel_peak(key, count, time=0):
    if not get_config_boolean('show_peaks'):
        return
    if key in channel_peak_hooks:
        weechat.unhook(channel_peak_hooks[key][0])
        time = channel_peak_hooks[key][1]
    else:
        time -= 60 * msg_queue_timeout # add delay in showing the msg

    if time:
        elapsed = time_elapsed(now() - time)
        if elapsed:
            elapsed = '(last peak was %s ago)' %elapsed
    else:
        elapsed = ''

    # hook it for show msg 10 min later
    channel_peak_hooks[key] = (weechat.hook_timer(60000 * msg_queue_timeout, 0, 1, 'new_channel_peak_cb',
            '%s,%s,New user peak: %s users %s' %(key[0], key[1], count, elapsed)), time)

def new_channel_peak_cb(data, count):
    debug(data)
    server, channel, s = data.split(',', 2)
    buffer = weechat.info_get('irc_buffer', '%s,%s' %(server, channel))
    if buffer:
        say('%s%s' %(color_peak, s), buffer=buffer)
    else:
        debug('XX falied to get buffer: %s.%s', args=(server, channel))
    del channel_peak_hooks[server, channel]
    return WEECHAT_RC_OK

channel_low_hooks = CaseInsensibleDict()
def new_channel_low(key, count, time=0):
    if not get_config_boolean('show_lows'):
        return
    if key in channel_low_hooks:
        weechat.unhook(channel_low_hooks[key][0])
        time = channel_low_hooks[key][1]
    else:
        time -= 60 * msg_queue_timeout # add delay in showing the msg

    if time:
        elapsed = time_elapsed(now() - time)
        if elapsed:
            elapsed = '(last low was %s ago)' %elapsed
    else:
        elapsed = ''

    # hook it for show msg 10 min later
    channel_low_hooks[key] = (weechat.hook_timer(60000 * msg_queue_timeout, 0, 1, 'new_channel_low_cb',
            '%s,%s,New user low: %s %s' %(key[0], key[1], count, elapsed)), time)

def new_channel_low_cb(data, count):
    debug(data)
    server, channel, s = data.split(',', 2)
    buffer = weechat.buffer_search('irc', '%s.%s' %(server, channel))
    if buffer:
        say('%s%s' %(color_low, s), buffer=buffer)
    else:
        debug('XX falied to get buffer: %s.%s', args=(server, channel))
    del channel_low_hooks[server, channel]
    return WEECHAT_RC_OK

# chanstat command
def chanstat_cmd(data, buffer, args):
    if args == '--save':
        write_database()
        channel_stats.close()
        say('Channel statistics saved.')
        return WEECHAT_RC_OK
    elif args == '--load':
        load_database()
        say('Channel statistics loaded.')
        return WEECHAT_RC_OK
#    elif args == '--print':
#        prnt = weechat.command

    channel = weechat.buffer_get_string(buffer, 'localvar_channel')
    server = weechat.buffer_get_string(buffer, 'localvar_server')
    key = (server, channel)

    update_user_count(server, channel)
    # clear any update in queue
    if key in update_channel_hook:
        weechat.unhook(update_channel_hook[key][0])
        del update_channel_hook[key]

    try:
        chan = channel_stats[server, channel]
        _now = now()
        peak_time = time_elapsed(_now - chan.max_date)
        low_time = time_elapsed(_now - chan.min_date)
        if peak_time:
            peak_time = ' (%s ago)' %peak_time
        if low_time:
            low_time = ' (%s ago)' %low_time
        if chan.avrg_period > time_hour:
            average = ' average: %s%.2f%s users (%s period)' %(color_avg, chan.average,
                    color_reset, time_elapsed(chan.avrg_period, level=1))
        else:
            average = ' (no average yet)'
        say('%s%s%s user peak: %s%s%s%s lowest: %s%s%s%s%s' %(
            color_bold, channel, color_reset,
            color_peak, chan.max, color_reset,
            peak_time,
            color_low, chan.max - chan.min, color_reset,
            low_time, average), buffer=buffer)

        # clear any new peak or low msg in queue
        if key in channel_peak_hooks:
            weechat.unhook(channel_peak_hooks[key][0])
            del channel_peak_hooks[key]
        if key in channel_low_hooks:
            weechat.unhook(channel_low_hooks[key][0])
            del channel_low_hooks[key]
    except KeyError:
        say('No statistics available.', buffer=buffer)

    return WEECHAT_RC_OK

def cmd_debug(data, buffer, args):
    dbg = lambda s, a: debug(s, args=a, name_suffix='dump')
    dbg('\nStats DB: %s', len(channel_stats))
    for key in channel_stats.keys():
        dbg('%s %s - %s', (key[0], key[1], channel_stats[key]))

    dbg('\nUsers: %s', len(domain_list))
    return WEECHAT_RC_OK

class Queue(dict):
    """User queue, for ignore many joins from same host (clones)"""
    def __contains__(self, key):
        self.clear()
        return dict.__contains__(self, key)

    def clear(self):
        _now = now()
        for key, time in self.items():
            if (_now - time) > 60:
                #debug('clearing domain %s from list (count: %s)' %(key, len(self)))
                del self[key]

domain_list = Queue()


# signal callbacks
def join_cb(data, signal, signal_data):
    #debug('%s  %s\n%s' %(data, signal, signal_data), 'SIGNAL')
    global netsplit
    if netsplit:
        debug('ignoring, netsplit')
        if (now() - netsplit) > 30*60: # wait 30 min
            netsplit = 0
        return WEECHAT_RC_OK

    server = signal[:signal.find(',')]
    signal_data = signal_data.split()
    channel = signal_data[2].strip(':')
    host = signal_data[0].strip(':')
    domain = '%s,%s' %(channel, host[host.find('@')+1:])
    if domain in domain_list:
        #debug('ignoring %s', args=domain)
        return WEECHAT_RC_OK
    else:
        domain_list[domain] = now()
    debug(' -- ping %s (%s)', args=(channel,signal[-4:]))
    add_update_user_hook(server, channel)
    return WEECHAT_RC_OK

netsplit = 0
def quit_cb(data, signal, signal_data):
    #debug('%s  %s\n%s' %(data, signal, signal_data), 'SIGNAL')
    global netsplit
    if netsplit:
        return WEECHAT_RC_OK
    quit_msg = signal_data[signal_data.rfind(':')+1:]
    if quit_msg_is_split(quit_msg):
        netsplit = now()
        for hook, when in update_channel_hook.itervalues():
            weechat.unhook(hook)
        update_channel_hook.clear()
        debug('NETSPLIT')

    return WEECHAT_RC_OK

def quit_msg_is_split(s):
    #if 'peer' in s: return True
    if s.count(' ') == 1:
        sp = s.find(' ')
        d1 = s.find('.')
        d2 = s.rfind('.')
        if 0 < d1 and 4 < d2 and d1 < sp < d2 and d2 + 1 < len(s):
            return True
    return False

update_channel_hook = CaseInsensibleDict()
update_queue_timeout = 120
def add_update_user_hook(server, channel):
    key = (server, channel)
    if key in update_channel_hook:
        hook, when = update_channel_hook[key]
        if (now() - when) > update_queue_timeout//2:
            debug(' vv rescheduling %s', args=key[1])
            weechat.unhook(hook)
        else:
            return
    else:
        debug(' >> scheduling %s', args=key[1])

    # we schedule the channel check for later so we can filter quick joins/parts and netsplits
    update_channel_hook[key] = (weechat.hook_timer(update_queue_timeout * 1000, 0, 1, 'update_user_count_cb',
            ','.join(key)), now())

def update_user_count_cb(data, count):
    server, channel = data.split(',', 1)
    channels = [ chan for serv, chan in update_channel_hook if server == serv ]
    if channels:
        update_user_count(server, channels)
        for chan in channels:
            hook, when = update_channel_hook[server, chan]
            weechat.unhook(hook)
            del update_channel_hook[server, chan]
    return WEECHAT_RC_OK

def script_load():
    load_database()
    update_user_count()

def script_unload():
    write_database()
    channel_stats.close()
    return WEECHAT_RC_OK

# default settings
settings = {
    'path'   :'%h/chanstat',
    'average_period':'30',
    'show_peaks' :'on',
    'show_lows'  :'on',
    }

if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, 'script_unload', ''):
    
    # colors
    color_delimiter = weechat.color('chat_delimiters')
    color_chat_nick = weechat.color('chat_nick')
    color_reset     = weechat.color('reset')
    color_peak      = weechat.color('green')
    color_low       = weechat.color('red')
    color_avg       = weechat.color('brown')
    color_bold      = weechat.color('white')

    # pretty [chanop]
    script_nick = '%s[%s%s%s]%s' %(color_delimiter, color_chat_nick, SCRIPT_NAME, color_delimiter,
            color_reset)

    for opt, val in settings.iteritems():
		if not weechat.config_is_set_plugin(opt):
			weechat.config_set_plugin(opt, val)

    script_load()

    weechat.hook_signal('*,irc_in2_join', 'join_cb', '')
    weechat.hook_signal('*,irc_in2_part', 'join_cb', '')
    weechat.hook_signal('*,irc_in2_quit', 'quit_cb', '')

    weechat.hook_command('chanstat', "Display channel's statistics.", '[--save | --load]',
            "Displays channel peak, lowest and average users for current channel.\n"
            "  --save: forces saving the stats database.\n"
            "  --load: forces loading the stats database (Overwriting actual values).\n",
            #" --print: sends /chanstat output to the current channel.",
            '--save|--load', 'chanstat_cmd', '')

    weechat.hook_command('chanstat_debug', '', '', '', '', 'cmd_debug', '')

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
