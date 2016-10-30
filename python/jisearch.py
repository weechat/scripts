# -*- coding: utf-8 -*-
#
# ark <quentrg@gmail.com>
# GitHub: Ark444
#
# The MIT License (MIT)
#
# Copyright (c) 2016 ark
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import weechat

info = (
        'jisearch',
        'ark',
        '0.1',
        'MIT',
        'Requests the jisho\'s API',
        '',
        'utf-8'
        )

def jisho_search(data, buffer, message):
    weechat.hook_process('url:http://beta.jisho.org/api/v1/search/words?keyword=' + message, 30 * 1000, 'jisearch_process_cb', '')
    return weechat.WEECHAT_RC_OK

def jisearch_process_cb(data, command, rc, out, err):
    result = b'[JiSearch] '
    try:
        page_data = json.loads(out)['data'][0]

        try:
            result += b'kanji: %s | ' % page_data['japanese'][0]['word'].encode('utf-8')
        except KeyError:
            pass
        result += b'reading: %s | ' % page_data['japanese'][0]['reading'].encode('utf-8')
        result += b'meaning: %s' % page_data['senses'][0]['english_definitions'][0].encode('utf-8')

    except:
        result += 'no results found.'
    weechat.prnt(weechat.current_buffer(), result)
    return weechat.WEECHAT_RC_OK

if weechat.register(*info):
    weechat.hook_command(
            'jisearch',
            'Calls Jisho\'s API to search for english words, kanji or kana.\n'
            'Output is printed on current buffer.\n\n'
            'example:\n'
            '\tInput:  /jisearch 私\n'
            '\tOutput: [JiSearch] kanji: 私 | reading: わたし | meaning: I\n'
            '\n'
            '\tInput:  /jisearch test\n'
            '\tOutput: [JiSearch] reading: テスト | meaning: test\n',
            '[kanji | kana | english]',
            '',
            '',
            'jisho_search',
            '')


