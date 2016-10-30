"""
Charlie Allom <charlie@evilforbeginners.com>

database init code from https://weechat.org/scripts/source/triggerreply.py.html
regex is from http://stackoverflow.com/questions/6883049/regex-to-find-urls-in-string-in-python

TODO
----
 - set a preference value for ignoring:
  - nicks
  - channels
 - purge sql rows after an age range (or fixed size)
 - ignore parts/quits messages
"""

SCRIPT_NAME = "url_olde"
SCRIPT_AUTHOR = "Charlie Allom <charlie@evilforbeginners.com"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "tells you how long ago a URL was first posted and by whom, for bragging rights."

try:
    import weechat as w
    import sqlite3, time, re
    from urlparse import urlparse
    IMPORT_ERR = 0
except ImportError:
    IMPORT_ERR = 1
import os


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
    full_uri = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message) # i didn't write this. close enough is good enough for now.
    channel = w.buffer_get_string(buffer, 'name') # current channel.
    for olde in full_uri: # iterate over each URI we get in the list from full_uri regex
        uri = urlparse(olde).hostname + urlparse(olde).path.rstrip("/)") # strip the final / and lesser-seen )
        new_entry = [] # create an ordered list of the following values we want to INSERT -> sql later on
        new_entry.append(uri)
        new_entry.append(time.time())
        new_entry.append(nick)
        new_entry.append(channel)
        cursor.execute("SELECT date,uri,nick,channel from urls WHERE uri LIKE ?", (uri,))
        result=cursor.fetchone()
        if result is None:
            """ a new URL is seen! """
            #w.command(buffer, "/notice %s"  % (new_entry)) #debug
            cursor.execute("INSERT INTO urls(uri, date, nick, channel) VALUES (?,?,?,?)", new_entry)
            database.commit()
        else:
            """ we've got a match from sqlite """
            date, uri, nick, channel = result
            timestamp = time.strftime('%Y-%m-%d', time.localtime(date)) # convert it to YYYY-MM-DD
            #w.command(buffer, "/notice DING %s"  % str(result)) # debug
            w.prnt_date_tags(buffer, 0, 'no_log,notify_none', 'olde!! already posted by %s in %s on %s' % (nick, channel, timestamp))
    return w.WEECHAT_RC_OK


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
           SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
    if IMPORT_ERR:
        w.prnt("", "You need sqlite3 to run this plugin.")
    DBFILE = "%s/olde.sqlite3" % w.info_get("weechat_dir", "")
    if not os.path.isfile(DBFILE):
        create_db() # init on load if file doesn't exist.

    # catch urls in buffer and send to the cb
    w.hook_print('', '', '://', 1, 'search_urls_cb', '')

    # test
    #w.prnt(w.current_buffer(), "script loaded!")
