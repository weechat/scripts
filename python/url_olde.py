# -*- coding: utf-8 -*-
"""
database init code from https://weechat.org/scripts/source/triggerreply.py.html
regex is from http://stackoverflow.com/questions/520031/whats-the-cleanest-way-to-extract-urls-from-a-string-using-python

TODO
----
 - set a preference value for ignoring:
  - nicks
 - purge sql rows after an age range (or fixed size)
"""

SCRIPT_NAME = "url_olde"
SCRIPT_AUTHOR = "Charlie Allom <charlie@evilforbeginners.com"
SCRIPT_VERSION = "0.6"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "tells you how long ago a URL was first posted and by whom, for bragging rights."

try:
    import weechat as w
    import sqlite3
    import time
    import re
    from urlparse import urldefrag
    IMPORT_ERR = 0
except ImportError:
    IMPORT_ERR = 1
import os

# plugins.var.python.url_olde.ignore_channel
url_olde_settings_default = {
    'ignored_channels': ('chanmon', 'comma separated list of buffers you want ignored. eg. freenode.#channelname')
}
url_olde_settings = {}


def create_db():
    """ create the sqlite database and insert a test URI as id 1 """
    tmpcon = sqlite3.connect(DBFILE)
    cur = tmpcon.cursor()
    cur.execute("CREATE TABLE urls(id INTEGER PRIMARY KEY, uri VARCHAR, date INTEGER, nick VARCHAR, channel VARCHAR);")
    cur.execute("INSERT INTO urls(uri, date, nick, channel) VALUES ('test.com',1,'donald_trump','hello.#world');")
    tmpcon.commit()
    cur.close()


def search_urls_cb(data, buffer, date, tags, displayed, highlight, prefix, message):
    """ searching for the url function
    message is the line that matched '://'
    buffer needs buffer_get_string for the short name
    prefix is nick
    """
    database = sqlite3.connect(DBFILE)
    database.text_factory = str
    cursor = database.cursor()
    nick = prefix
    full_uri = re.findall(r'(?:(?:https?|ftp)://)(?:\S+(?::\S*)?@)?(?:(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:/[^\s]*)?', message)
    channel = w.buffer_get_string(buffer, 'name')  # current channel.
    # w.prnt(w.current_buffer(), 'full_uri: %s ' % (full_uri)) # debug
    for olde in full_uri:  # iterate over each URI we get in the list from full_uri regex
        if '/#/' in olde:  # run this routine on rails style apps
            url = olde
            uri = url.rstrip("/)")  # strip the final / and lesser-seen )
            new_entry = []  # create an ordered list of the following values we want to INSERT -> sql later on
            new_entry.append(uri)
            new_entry.append(time.time())
            new_entry.append(nick)
            new_entry.append(channel)
            # w.prnt(w.current_buffer(), 'uri: %s ' % (uri)) # debug
            cursor.execute("SELECT date,uri,nick,channel from urls WHERE uri = ?", (uri,))
            result = cursor.fetchone()
            if channel in str(url_olde_settings['ignored_channels']):
                # w.prnt(w.current_buffer(), 'ignoring %s due to ignored_channels = %s' % (uri, str(url_olde_settings['ignored_channels'])))
                return w.WEECHAT_RC_OK
            if result is None:
                """ a new URL is seen! """
                # w.command(buffer, "/notice %s"  % (new_entry))  # debug
                cursor.execute("INSERT INTO urls(uri, date, nick, channel) VALUES (?,?,?,?)", new_entry)
                database.commit()
            else:
                """ we've got a match from sqlite """
                date, uri, nick, channel = result
                timestamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(date))  # convert it to YYYY-MM-DD
                # w.command(buffer, "/notice DING %s"  % str(result)) # debug
                w.prnt_date_tags(buffer, 0, 'no_log,notify_none', 'olde!! already posted by %s in %s on %s' % (nick, channel, timestamp))
        else:  # strip anchors
            url, fragment = urldefrag(olde)
            uri = url.rstrip("/)")  # strip the final / and lesser-seen )
            new_entry = []  # create an ordered list of the following values we want to INSERT -> sql later on
            new_entry.append(uri)
            new_entry.append(time.time())
            new_entry.append(nick)
            new_entry.append(channel)
            # w.prnt(w.current_buffer(), 'uri: %s ' % (uri)) # debug
            cursor.execute("SELECT date,uri,nick,channel from urls WHERE uri = ?", (uri,))
            result = cursor.fetchone()
            if channel in str(url_olde_settings['ignored_channels']):
                # w.prnt(w.current_buffer(), 'ignoring %s due to ignored_channels = %s' % (uri, str(url_olde_settings['ignored_channels'])))
                return w.WEECHAT_RC_OK
            if result is None:
                """ a new URL is seen! """
                # w.command(buffer, "/notice %s"  % (new_entry))  # debug
                cursor.execute("INSERT INTO urls(uri, date, nick, channel) VALUES (?,?,?,?)", new_entry)
                database.commit()
            else:
                """ we've got a match from sqlite """
                date, uri, nick, channel = result
                timestamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(date))  # convert it to YYYY-MM-DD
                # w.command(buffer, "/notice DING %s"  % str(result)) # debug
                w.prnt_date_tags(buffer, 0, 'no_log,notify_none', 'olde!! already posted by %s in %s on %s' % (nick, channel, timestamp))
    return w.WEECHAT_RC_OK


def url_olde_load_config():
    global url_olde_settings_default, url_olde_settings
    version = w.info_get('version_number', '') or 0
    for option, value in url_olde_settings_default.items():
        if w.config_is_set_plugin(option):
            url_olde_settings[option] = w.config_get_plugin(option)
        else:
            w.config_set_plugin(option, value[0])
            url_olde_settings[option] = value[0]
        if int(version) >= 0x00030500:
            w.config_set_desc_plugin(option, value[1])


def url_olde_config_cb(data, option, value):
    """Called each time an option is changed."""
    url_olde_load_config()
    return w.WEECHAT_RC_OK


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
              SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
    if IMPORT_ERR:
        w.prnt("", "You need sqlite3 to run this plugin.")
    DBFILE = "%s/olde.sqlite3" % w.info_get("weechat_dir", "")
    if not os.path.isfile(DBFILE):
        create_db()  # init on load if file doesn't exist.

    # load the config
    url_olde_load_config()
    # config changes are reloaded
    w.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'url_olde_config_cb', '')
    # catch urls in buffer and send to the cb
    w.hook_print('', 'irc_privmsg', '://', 1, 'search_urls_cb', '')
