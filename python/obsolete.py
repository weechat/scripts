#!/usr/bin/python
# -*- encoding: utf-8 -*-
"""
  Script to check if your scripts are up to date with list located at
  http://weechat.flashtux.org/plugins.php, only loaded scripts are
  checked.
  Parsing the information related to loaded scripts is full of hacks, 
  but it works somehow. :)

  The script works with weechat 0.2.6 and needs curl to fetch data from
  the website. Curl is used as I'm a bit afraid of using threads in 
  weechat.
  The script adds command /obsolete that will show you list of packages
  that has different version and/or are not registered at the scrtips
  repository.

  The script is in the public domain.
  Leonid Evdokimov (weechat at darkk dot net dot ru)
  http://darkk.net.ru/weechat/obsolete.py

0.1  - initial commit
"""

import weechat
import sre
import sys
from subprocess import Popen
from tempfile import TemporaryFile
from xml.dom import Node
from xml.dom.minidom import parse
from itertools import ifilter

NAME = 'obsolete'
VERSION = '0.1'

class WeePrint(object):
    """ thanks EgS for cool idea (copy-paste from toggle.py)"""
    def write(self, text):
        text = text.rstrip(' \0\n')                                    # strip the null byte appended by pythons print
        if text:
            text = '[' + NAME + '] '+ text
            weechat.prnt(text,'')

def isPluginDiv(node):
    return node.getAttributeNode('class') and node.getAttributeNode('class').nodeValue == u'pluginlist'

def fmtAssert(bool):
    if not bool:
        raise RuntimeError, "webpage format changed"

def getTextNodeChild(node):
    fmtAssert(len(node.childNodes) == 1)
    child = node.firstChild
    fmtAssert(child.nodeType == Node.TEXT_NODE)
    return child.nodeValue

def xor(a, b):
    return (a and not b) or (not a and b)

downloaders = []
def Downloader_poll():
    if len(downloaders) == 0:
        weechat.remove_timer_handler("Downloader_poll")

    for d in downloaders[:]:
        if d.poll() != None:
            downloaders.remove(d)
            d.run()

    return weechat.PLUGIN_RC_OK
        
class Downloader(Popen):
    def __init__(self, url, ok):
        self._stdout = TemporaryFile()
        self._stderr = TemporaryFile()
        self._ok = ok
        Popen.__init__(self, ['curl', '--silent', '--show-error', '--fail', url], stdout = self._stdout, stderr = self._stderr)
        add_timer = not downloaders
        downloaders.append(self)
        if add_timer:
            weechat.add_timer_handler(1, "Downloader_poll")

    def run(self):
        if self.poll() == 0:
            f = self._ok
        else:
            def fail(stdout, stderr):
                print "curl failed, exit code %i:" % self.poll()
                for line in stderr:
                    print line
            f = fail
        self._stdout.seek(0)
        self._stderr.seek(0)
        f(self._stdout, self._stderr)


class Version:
    def __init__(self, str):
        self._ver = [int(chunk) for chunk in str.split('.')]
    def __str__(self):
        return '.'.join([str(chunk) for chunk in self._ver])
    def __eq__(self, that):
        return self._ver == that._ver
    def __lt__(self, that):
        return self._ver < that._ver

class Plugin:
    def __init__(self, name, ver, lang, url = None):
        self.name = name
        self.url = url
        self.ver = Version(ver)
        self.lang = lang
    def __str__(self):
        return "%s/%s" % (self.lang, self.name)

def parse_published(fd):
    plugins = {}
    doc = parse(fd)
    for div in ifilter(isPluginDiv, doc.getElementsByTagName('div')): 
        for table in ifilter(lambda n: n.nodeName == u'table', div.childNodes):
            for tr in ifilter(lambda n: n.nodeName == u'tr', table.childNodes):
                ths = tuple(ifilter(lambda n: n.nodeName == u'th', tr.childNodes))
                tds = tuple(ifilter(lambda n: n.nodeName == u'td', tr.childNodes))
                fmtAssert(xor(ths, tds))
                if ths:
                    headers = []
                    for th in ths[0:3]:
                        fmtAssert(len(th.childNodes) == 1)
                        a = th.childNodes[0]
                        fmtAssert(a.nodeName == u'a')
                        headers.append(getTextNodeChild(a))
                    fmtAssert(tuple(headers) == (u'Name', u'Version', u'Language'))
                if tds:
                    fmtAssert(len(tds[0].childNodes) == 1)
                    a = tds[0].firstChild
                    fmtAssert(a.nodeName == u'a')
                    href = a.getAttributeNode('href')
                    fmtAssert(href)
                    url = getTextNodeChild(href)
                    name = getTextNodeChild(a)
                    ver = getTextNodeChild(tds[1])
                    lang = getTextNodeChild(tds[2])
                    plugins.setdefault(lang.lower(), {})
                    plugins[lang.lower()][name.lower()] = Plugin(name, ver, lang, url)
    return plugins

def get_cmd_output(cmd, serv, channel = ''):
    offset = len(weechat.get_buffer_data(serv, channel))
    weechat.command(cmd, channel, serv)
    data = weechat.get_buffer_data(serv, channel)
    data.reverse()
    data = data[offset:]
    return [l['data'] for l in data]

def get_known_languages(serv):
    lines = get_cmd_output('/plugin', serv)
    pairs = {
        '-P-   Perl v': 'Perl',
        '-P-   Python v': 'Python',
        '-P-   Lua v': 'Lua',
        '-P-   Ruby v': 'Ruby',
    }
    retval = []
    for line in lines:
        for key, value in pairs.iteritems():
            if line.lower().find(key.lower()) == 0:
                retval.append(value)
    return retval

def get_installed(serv, lang):
    cmd = '/%s' % lang.lower()
    lines = get_cmd_output(cmd, serv)
    parse = False
    retval = []
    for line in lines:
        if parse:
            match = sre.match(r'-P-   (.*) v([0-9\.]+) - .*', line)
            if match:
                name = match.group(1)
                ver = match.group(2)
                retval.append(Plugin(name, ver, lang))
        if line == ('-P- Registered %s scripts:' % lang):
            parse = True
        if line == ('-P- %s message handlers:' % lang):
            break
    return retval



def do_obsolete(serv, args):
    def callback(stdout, stderr):
        plugins = parse_published(stdout)
        do_obsolete_finish(serv, plugins)
    Downloader('http://weechat.flashtux.org/plugins.php', callback)
    return weechat.PLUGIN_RC_OK

def do_obsolete_finish(serv, plugins):
    known_languages = get_known_languages(serv)

    installed = {}
    for lang in known_languages:
        installed[lang.lower()] = get_installed(serv, lang)
    
    for lang in known_languages:
        for script in installed[lang.lower()]:
            last = plugins[lang.lower()].get(script.name.lower())
            if last:
                if last.ver > script.ver:
                    print "%s is not up to date: %s installed, %s exists (%s)" % (script, script.ver, last.ver, last.url)
                elif last.ver < script.ver:
                    print "%s is newer then published one: %s installed, %s published" % (script, script.ver, last.ver)
            else:
                print "%s is not published at all" % (script)


if weechat.register(NAME, VERSION, "", "tracks up to date information about scripts"):
    sys.stdout = WeePrint()
    weechat.add_command_handler("obsolete", "do_obsolete", "show loaded plugins that are obsolete")
                    
# vim:set tabstop=4 softtabstop=4 shiftwidth=4: 
# vim:set foldmethod=marker foldlevel=32 foldmarker={{{,}}}: 
# vim:set expandtab: 
