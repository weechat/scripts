# -*- coding: utf-8 -*-
###
# Copyright (c) 2009-2011 by Elián Hanisch <lambdae2@gmail.com>
# Copyright (c) 2013 by Filip H.F. "FiXato" Slagter <fixato+weechat@gmail.com>
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
# Prints user's country and local time information in
# whois/whowas replies (for WeeChat 0.3.*)
#
#   This script uses MaxMind's GeoLite database from
#   http://www.maxmind.com/app/geolitecountry
#
#   This script depends in pytz third party module for retrieving
#   timezone information for a given country. Without it the local time
#   for a user won't be displayed.
#   Get it from http://pytz.sourceforge.net or from your distro packages,
#   python-tz in Ubuntu/Debian
#
#   Commands:
#   * /country
#     Prints country for a given ip, uri or nick. See /help country
#
#   Settings:
#   * plugins.var.python.country.show_in_whois:
#     If 'off' /whois or /whowas replies won't contain country information.
#     Valid values: on, off
#   * plugins.var.python.country.show_localtime:
#     If 'off' timezone and local time infomation won't be looked for.
#     Valid values: on, off
#
#
#   TODO
#   * Add support for IPv6 addresses
#
#
#   History:
#   2013-04-28
#   version 0.6:
#   * Improved support for target msgbuffer. Takes the following settings into account:
#       - irc.msgbuffer.whois
#       - irc.msgbuffer.$servername.whois
#       - irc.look.msgbuffer_fallback
#
#   2011-08-14
#   version 0.5:
#   * make time format configurable.
#   * print to private buffer based on msgbuffer setting.
#
#   2011-01-09
#   version 0.4.1: bug fixes
#
#   2010-11-15
#   version 0.4:
#   * support for users using webchat (at least in freenode)
#   * enable Archlinux workaround.
#
#   2010-01-11
#   version 0.3.1: bug fix
#   * irc_nick infolist wasn't freed in get_host_by_nick()
#
#   2009-12-12
#   version 0.3: update WeeChat site.
#
#   2009-09-17
#   version 0.2: added timezone and local time information.
#
#   2009-08-24
#   version 0.1.1: fixed python 2.5 compatibility.
#
#   2009-08-21
#   version 0.1: initial release.
#
###

SCRIPT_NAME    = "country"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.6.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Prints user's country and local time in whois replies"
SCRIPT_COMMAND = "country"

try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt
    import_ok = True
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

try:
    import pytz, datetime
    pytz_module = True
except:
    pytz_module = False

import os, re, socket

### ip database
database_url = 'http://geolite.maxmind.com/download/geoip/database/GeoIPCountryCSV.zip'
database_file = 'GeoIPCountryWhois.csv'

### config
settings = {
        'time_format': '%x %X %Z',
        'show_in_whois': 'on',
        'show_localtime': 'on'
        }

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

### messages

script_nick = SCRIPT_NAME
def error(s, buffer=''):
    """Error msg"""
    prnt(buffer, '%s%s %s' % (weechat.prefix('error'), script_nick, s))
    if weechat.config_get_plugin('debug'):
        import traceback
        if traceback.sys.exc_type:
            trace = traceback.format_exc()
            prnt('', trace)

def say(s, buffer=''):
    """normal msg"""
    prnt(buffer, '%s\t%s' % (script_nick, s))

def whois(nick, string, buffer=''):
    """Message formatted like a whois reply."""
    prefix_network = weechat.prefix('network')
    color_delimiter = weechat.color('chat_delimiters')
    color_nick = weechat.color('chat_nick')
    prnt(buffer, '%s%s[%s%s%s] %s' % (prefix_network,
                                      color_delimiter,
                                      color_nick,
                                      nick,
                                      color_delimiter,
                                      string))

def string_country(country, code):
    """Format for country info string."""
    color_delimiter = weechat.color('chat_delimiters')
    color_chat = weechat.color('chat')
    return '%s%s %s(%s%s%s)' % (color_chat,
                                country,
                                color_delimiter,
                                color_chat,
                                code,
                                color_delimiter)

def string_time(dt):
    """Format for local time info string."""
    if not dt: return '--'
    color_delimiter = weechat.color('chat_delimiters')
    color_chat = weechat.color('chat')
    date = dt.strftime(weechat.config_get_plugin("time_format"))
    tz = dt.strftime('UTC%z')
    return '%s%s %s(%s%s%s)' % (color_chat,
                                date,
                                color_delimiter,
                                color_chat,
                                tz,
                                color_delimiter)

### functions
def get_script_dir():
    """Returns script's dir, creates it if needed."""
    script_dir = weechat.info_get('weechat_dir', '')
    script_dir = os.path.join(script_dir, 'country')
    if not os.path.isdir(script_dir):
        os.makedirs(script_dir)
    return script_dir

ip_database = ''
def check_database():
    """Check if there's a database already installed."""
    global ip_database
    if not ip_database:
        ip_database = os.path.join(get_script_dir(), database_file)
    return os.path.isfile(ip_database)

timeout = 1000*60*10
hook_download = ''
def update_database():
    """Downloads and uncompress the database."""
    global hook_download, ip_database
    if not ip_database:
        check_database()
    if hook_download:
        weechat.unhook(hook_download)
        hook_download = ''
    script_dir = get_script_dir()
    say("Downloading IP database...")
    python_bin = weechat.info_get('python2_bin', '') or 'python'
    hook_download = weechat.hook_process(
            python_bin + " -c \"\n"
            "import urllib2, zipfile, os, sys\n"
            "try:\n"
            "   temp = os.path.join('%(script_dir)s', 'temp.zip')\n"
            "   try:\n"
            "       zip = urllib2.urlopen('%(url)s', timeout=10)\n"
            "   except TypeError: # python2.5\n"
            "       import socket\n"
            "       socket.setdefaulttimeout(10)\n"
            "       zip = urllib2.urlopen('%(url)s')\n"
            "   fd = open(temp, 'w')\n"
            "   fd.write(zip.read())\n"
            "   fd.close()\n"
            "   print('Download complete, uncompressing...')\n"
            "   zip = zipfile.ZipFile(temp)\n"
            "   try:\n"
            "       zip.extractall(path='%(script_dir)s')\n"
            "   except AttributeError: # python2.5\n"
            "       fd = open('%(ip_database)s', 'w')\n"
            "       fd.write(zip.read('%(database_file)s'))\n"
            "       fd.close()\n"
            "   os.remove(temp)\n"
            "except Exception as e:\n"
            "   print(e, file=sys.stderr)\n\"" % {'url':database_url,
                                              'script_dir':script_dir,
                                              'ip_database':ip_database,
                                              'database_file':database_file
                                              },
            timeout, 'update_database_cb', '')

process_stderr = ''
def update_database_cb(data, command, rc, stdout, stderr):
    """callback for our database download."""
    global hook_download, process_stderr
    #debug("%s @ stderr: '%s', stdout: '%s'" %(rc, stderr.strip('\n'), stdout.strip('\n')))
    if stdout:
        say(stdout)
    if stderr:
        process_stderr += stderr
    if int(rc) >= 0:
        if process_stderr:
            error(process_stderr)
            process_stderr = ''
        else:
            say('Success.')
        hook_download = ''
    return WEECHAT_RC_OK

hook_get_ip = ''
def get_ip_process(host):
    """Resolves host to ip."""
    # because getting the ip might take a while, we must hook a process so weechat doesn't hang.
    global hook_get_ip
    if hook_get_ip:
        weechat.unhook(hook_get_ip)
        hook_get_ip = ''
    python_bin = weechat.info_get('python2_bin', '') or 'python'
    hook_get_ip = weechat.hook_process(
            python_bin + " -c \"\n"
            "import socket, sys\n"
            "try:\n"
            "   ip = socket.gethostbyname('%(host)s')\n"
            "   print(ip)\n"
            "except Exception as e:\n"
            "   print(e, file=sys.stderr)\n\"" %{'host':host},
            timeout, 'get_ip_process_cb', '')

def get_ip_process_cb(data, command, rc, stdout, stderr):
    """Called when uri resolve finished."""
    global hook_get_ip, reply_wrapper
    #debug("%s @ stderr: '%s', stdout: '%s'" %(rc, stderr.strip('\n'), stdout.strip('\n')))
    if stdout and reply_wrapper:
        code, country = search_in_database(stdout[:-1])
        reply_wrapper(code, country)
        reply_wrapper = None
    if stderr and reply_wrapper:
        reply_wrapper(*unknown)
        reply_wrapper = None
    if int(rc) >= 0:
        hook_get_ip = ''
    return WEECHAT_RC_OK

def is_ip(s):
    """Returns whether or not a given string is an IPV4 address."""
    try:
        return bool(socket.inet_aton(s))
    except socket.error:
        return False

_valid_label = re.compile(r'^([\da-z]|[\da-z][-\da-z]*[\da-z])$', re.I)
def is_domain(s):
    """
    Checks if 's' is a valid domain."""
    if not s or len(s) > 255:
        return False
    labels = s.split('.')
    if len(labels) < 2:
        return False
    for label in labels:
        if not label or len(label) > 63 \
                or not _valid_label.match(label):
            return False
    return True

def hex_to_ip(s):
    """
    '7f000001' => '127.0.0.1'"""
    try:
        ip = map(lambda n: s[n:n+2], range(0, len(s), 2))
        ip = map(lambda n: int(n, 16), ip)
        return '.'.join(map(str, ip))
    except:
        return ''

def get_userhost_from_nick(buffer, nick):
    """Return host of a given nick in buffer."""
    channel = weechat.buffer_get_string(buffer, 'localvar_channel')
    server = weechat.buffer_get_string(buffer, 'localvar_server')
    if channel and server:
        infolist = weechat.infolist_get('irc_nick', '', '%s,%s' %(server, channel))
        if infolist:
            try:
                while weechat.infolist_next(infolist):
                    name = weechat.infolist_string(infolist, 'name')
                    if nick == name:
                        return weechat.infolist_string(infolist, 'host')
            finally:
                weechat.infolist_free(infolist)
    return ''

def get_ip_from_userhost(user, host):
    ip = get_ip_from_host(host)
    if ip:
        return ip
    ip = get_ip_from_user(user)
    if ip:
        return ip
    return host

def get_ip_from_host(host):
    if is_domain(host):
        return host
    else:
        if host.startswith('gateway/web/freenode/ip.'):
            ip = host.split('.', 1)[1]
            return ip

def get_ip_from_user(user):
    user = user[-8:] # only interested in the last 8 chars
    if len(user) == 8:
        ip = hex_to_ip(user)
        if ip and is_ip(ip):
            return ip

def sum_ip(ip):
    """Converts the ip number from dot-decimal notation to decimal."""
    L = list(map(int, ip.split('.')))
    return L[0]*16777216 + L[1]*65536 + L[2]*256 + L[3]

unknown = ('--', 'unknown')
def search_in_database(ip):
    """
    search_in_database(ip_number) => (code, country)
    returns ('--', 'unknown') if nothing found
    """
    import csv
    global ip_database
    if not ip or not ip_database:
        return unknown
    try:
        # do a binary search.
        n = sum_ip(ip)
        fd = open(ip_database)
        reader = csv.reader(fd)
        max = os.path.getsize(ip_database)
        last_high = last_low = min = 0
        while True:
            mid = (max + min)/2
            fd.seek(mid)
            fd.readline() # move cursor to next line
            _, _, low, high, code, country = next(reader)
            if low == last_low and high == last_high:
                break
            if n < int(low):
                max = mid
            elif n > int(high):
                min = mid
            elif n > int(low) and n < int(high):
                return (code, country)
            else:
                break
            last_low, last_high = low, high
    except StopIteration:
        pass
    return unknown

def print_country(host, buffer, quiet=False, broken=False, nick=''):
    """
    Prints country and local time for a given host, if quiet is True prints only if there's a match,
    if broken is True reply will be split in two messages.
    """
    #debug('host: ' + host)
    def reply_country(code, country):
        if quiet and code == '--':
            return
        if pytz_module and get_config_boolean('show_localtime') and code != '--':
            dt = get_country_datetime(code)
            if broken:
                whois(nick or host, string_country(country, code), buffer)
                whois(nick or host, string_time(dt), buffer)
            else:
                s = '%s - %s' %(string_country(country, code), string_time(dt))
                whois(nick or host, s, buffer)
        else:
            whois(nick or host, string_country(country, code), buffer)

    if is_ip(host):
        # good, got an ip
        code, country = search_in_database(host)
    elif is_domain(host):
        # try to resolve uri
        global reply_wrapper
        reply_wrapper = reply_country
        get_ip_process(host)
        return
    else:
        # probably a cloak or ipv6
        code, country = unknown
    reply_country(code, country)

### timezone
def get_country_datetime(code):
    """Get datetime object with country's timezone."""
    try:
        tzname = pytz.country_timezones(code)[0]
        tz = pytz.timezone(tzname)
        return datetime.datetime.now(tz)
    except:
        return None

### commands
def cmd_country(data, buffer, args):
    """Shows country and local time for a given ip, uri or nick."""
    if not args:
        weechat.command('', '/HELP %s' %SCRIPT_COMMAND)
        return WEECHAT_RC_OK
    if ' ' in args:
        # picks the first argument only
        args = args[:args.find(' ')]
    if args == 'update':
        update_database()
    else:
        if not check_database():
            error("IP database not found. You must download a database with '/country update' before "
                    "using this script.", buffer)
            return WEECHAT_RC_OK
        #check if is a nick
        userhost = get_userhost_from_nick(buffer, args)
        if userhost:
            host = get_ip_from_userhost(*userhost.split('@'))
        else:
            host = get_ip_from_userhost(args, args)
        print_country(host, buffer)
    return WEECHAT_RC_OK

def find_buffer(server, nick, message_type='whois'):
    # See if there is a target msgbuffer set for this server
    msgbuffer = weechat.config_string(weechat.config_get('irc.msgbuffer.%s.%s' % (server, message_type)))
    # No whois msgbuffer for this server; use the global setting
    if msgbuffer == '':
        msgbuffer = weechat.config_string(weechat.config_get('irc.msgbuffer.%s' % message_type))

    # Use the fallback msgbuffer setting if private buffer doesn't exist
    if msgbuffer == 'private':
        buffer = weechat.buffer_search('irc', '%s.%s' %(server, nick))
        if buffer != '':
            return buffer
        else:
            msgbuffer = weechat.config_string(weechat.config_get('irc.look.msgbuffer_fallback'))

    # Find the appropriate buffer
    if msgbuffer == "current":
        return weechat.current_buffer()
    elif msgbuffer == "weechat":
        return weechat.buffer_search_main()
    else:
        return weechat.buffer_search('irc', 'server.%s' % server)

### signal callbacks
def whois_cb(data, signal, signal_data):
    """function for /WHOIS"""
    if not get_config_boolean('show_in_whois') or not check_database():
        return WEECHAT_RC_OK
    nick, user, host = signal_data.split()[3:6]
    server = signal[:signal.find(',')]
    #debug('%s | %s | %s' %(data, signal, signal_data))
    host = get_ip_from_userhost(user, host)
    print_country(host, find_buffer(server, nick), quiet=True, broken=True, nick=nick)
    return WEECHAT_RC_OK

### main
if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

    # colors
    color_delimiter = weechat.color('chat_delimiters')
    color_chat_nick = weechat.color('chat_nick')
    color_reset     = weechat.color('reset')

    # pretty [SCRIPT_NAME]
    script_nick = '%s[%s%s%s]%s' % (color_delimiter,
                                    color_chat_nick,
                                    SCRIPT_NAME,
                                    color_delimiter,
                                    color_reset)

    weechat.hook_signal('*,irc_in2_311', 'whois_cb', '') # /whois
    weechat.hook_signal('*,irc_in2_314', 'whois_cb', '') # /whowas
    weechat.hook_command('country', cmd_country.__doc__, 'update | (nick|ip|uri)',
            "       update: Downloads/updates ip database with country codes.\n"
            "nick, ip, uri: Gets country and local time for a given ip, domain or nick.",
            'update||%(nick)', 'cmd_country', '')

    # settings
    for opt, val in settings.items():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    if not check_database():
        say("IP database not found. You must download a database with '/country update' before "
                "using this script.")

    if not pytz_module and get_config_boolean('show_localtime'):
        error(
            "pytz module isn't installed, local time information is DISABLED. "
            "Get it from http://pytz.sourceforge.net or from your distro packages "
            "(python-tz in Ubuntu/Debian).")
        weechat.config_set_plugin('show_localtime', 'off')

    # -------------------------------------------------------------------------
    # Debug

    if weechat.config_get_plugin('debug'):
        try:
            # custom debug module I use, allows me to inspect script's objects.
            import pybuffer
            debug = pybuffer.debugBuffer(globals(), '%s_debug' % SCRIPT_NAME)
        except:
            def debug(s, *args):
                if not isinstance(s, basestring):
                    s = str(s)
                if args:
                    s = s %args
                prnt('', '%s\t%s' % (script_nick, s))
    else:
        def debug(*args):
            pass

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
