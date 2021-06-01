"""Copyright (c) 2021 The gitlab.com/mohan43u/weenotifier Authors.

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

   * Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.
   * Redistributions in binary form must reproduce the above
copyright notice, this list of conditions and the following disclaimer
in the documentation and/or other materials provided with the
distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

20210-07-01: Mohan R
      0.0.1: Initial release

Description: notifier using IrssiNotifier (https://irssinotifier.appspot.com/)
Project URL: https://gitlab.com/mohan43u/weenotifier
"""

import os
import base64
from urllib.parse import urlencode

try:
    import weechat
    weechat.register('weenotifier',
                     'Mohan R',
                     '0.0.1',
                     'BSD 2-Clause Simplified',
                     'notifier using \
                     IrssiNotifier (https://irssinotifier.appspot.com/)',
                     'shutdown_cb',
                     '')
except ImportError as exception:
    raise ImportError('This script has to run under \
    WeeChat (https://weechat.org/)') from exception


try:
    from cryptography.hazmat.primitives import hashes, ciphers, padding
except ImportError as exception:
    raise ImportError('failed to import cryptography module \
    (https://cryptography.io)') from exception


weenotifier = None


class WeeNotifier:
    """Weenotifier - primary class."""

    def __init__(self):
        """Weenotifier - initialization."""
        self.options = {
            'url': 'https://irssinotifier.appspot.com/API/Message',
            'token': '',
            'password': 'password'
        }

        for option, value in self.options.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, value)

        self.url = weechat.config_get_plugin('url')
        if self.url is None or len(self.url) <= 0:
            raise NameError('weenotifier: url not configured')

        self.token = weechat.config_get_plugin('token')
        if self.token is None or len(self.token) <= 0:
            raise NameError('weenotifier: token not configured')

        self.password = weechat.config_get_plugin('password')
        if self.password is None or len(self.password) <= 0:
            raise NameError('weenotifier: password not configured')

        self.version = weechat.info_get('version_number', '') or '0'
        weechat.hook_print('', '', '', 1, 'message_cb', '')

    def encrypt(self, password, data):
        """Encrypt given data using md5 + salt + aes-128-cbc."""
        # IrssiNotifier requires null at the end
        databytes = data.encode() + bytes(1)
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(databytes) + padder.finalize()
        salt = os.urandom(8)
        key = None
        iv = None

        for n in range(2):
            # this following logic is similar to EVP_BytesToKey() from openssl
            md5hash = hashes.Hash(hashes.MD5())
            if key is not None:
                md5hash.update(key)
            md5hash.update(password.encode())
            md5hash.update(salt)
            md5 = md5hash.finalize()
            if key is None:
                key = md5
                continue
            if iv is None:
                iv = md5

        aes256cbc = ciphers.Cipher(ciphers.algorithms.AES(key),
                                   ciphers.modes.CBC(iv))
        encryptor = aes256cbc.encryptor()
        edata = encryptor.update(padded_data) + encryptor.finalize()
        edata = 'Salted__'.encode() + salt + edata
        edata = base64.b64encode(edata, b'-_')
        edata = edata.replace(b'=', b'')
        return edata

    def message(self, data, buffer, date, tags, isdisplayed, ishighlight,
                prefix, message):
        """Send message to IrssiNotifier."""
        if int(ishighlight):
            channel = weechat.buffer_get_string(buffer, 'sort_name') or \
                weechat.buffer_get_string(buffer, 'name')
            post = urlencode({'apiToken': self.token,
                              'channel': self.encrypt(self.password, channel),
                              'nick': self.encrypt(self.password, prefix),
                              'message': self.encrypt(self.password, message),
                              'version': self.version})
            weechat.hook_process_hashtable('url:' + self.url,
                                           {'postfields': post}, 10000, '', '')
        return weechat.WEECHAT_RC_OK

    def shutdown(self):
        """Shutdown callback."""
        return weechat.WEECHAT_RC_OK


def message_cb(data, buffer, date, tags, isdisplayed, ishighlight, prefix,
               message):
    """Message callback Which will be called by weechat-C-api."""
    if weenotifier is not None:
        return weenotifier.message(data, buffer, date, tags, isdisplayed,
                                   ishighlight, prefix, message)
    return weechat.WEECHAT_RC_ERROR


def shutdown_cb():
    """Shutdown callback Which will be called by weechat-C-api."""
    if weenotifier is not None:
        return weenotifier.shutdown()
    return weechat.WEECHAT_RC_ERROR


def main():
    """Start point."""
    global weenotifier
    weenotifier = WeeNotifier()


if __name__ == '__main__':
    main()
