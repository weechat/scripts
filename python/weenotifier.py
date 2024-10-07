"""
Copyright (c) 2021-present Mohan Raman <mohan43u@gmail.com>.

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

2021-07-01: Mohan R
     0.0.1: Initial release with IrssiNotifier
            (https://irssinotifier.appspot.com/)

2024-10-06: Mohan R
     0.1.0: switched to gotify (https://gotify.net/)
            it should also support ntfy.sh (https://ntfy.sh)

Description: notifier for push notification
Project URL: https://gitlab.com/mohan43u/weenotifier
"""

from urllib.parse import urlencode

try:
    import weechat
    result = weechat.register("weenotifier",
                              "Mohan R",
                              "0.1.0",
                              "BSD 2-Clause Simplified",
                              "notifier for push notification",
                              "shutdown_cb",
                              "")
except ImportError as exception:
    raise ImportError("This script has to run under" +
                      "WeeChat (https://weechat.org/)") from exception


class WeeNotifier:
    """
    Weenotifier - primary class.
    """

    def __init__(self):
        """
        Weenotifier - initialization.
        """

        self.options = {
            "url": "",  # gotify: https://selfhostedgotify.yrdomain.tld/message
                        # ntfy.sh: https://ntfy.sh/youruniquetopic
            "token": ""
        }

        for option, value in self.options.items():
            if not weechat.config_is_set_plugin(option):
                _ = weechat.config_set_plugin(option,
                                              value)

        self.url = weechat.config_get_plugin("url")
        if len(self.url) <= 0:
            raise NameError("weenotifier: 'url' not configured")

        # for gotify
        token = weechat.config_get_plugin("token")
        if len(token) > 0:
            self.url += "?token=" + token

        self.version = weechat.info_get("version_number",
                                        "") or "0"
        _ = weechat.hook_print("",
                               "",
                               "",
                               1,
                               "message_cb",
                               "")

    def message(self,
                _data: str,
                buffer: str,
                _date: int,
                tags: list[str],
                _displayed: int,
                highlight: int,
                prefix: str,
                message: str):
        """
        Send message to push notification server.
        """

        if highlight or ("notify_private" in tags):
            channel = weechat.buffer_get_string(buffer, "short_name") or \
                weechat.buffer_get_string(buffer, "name")
            message = prefix + ": " + message
            post = channel + ": " + message

            # format for gotify
            if "?token=" in self.url:
                post = urlencode({"title": channel,
                                  "message": message,
                                  "priority": "4"})

            _ = weechat.hook_process_hashtable("url:" + self.url,
                                               {"post": "1",
                                                "postfields": post},
                                               10000,
                                               "result_cb",
                                               "")
        return weechat.WEECHAT_RC_OK

    def result(self,
               data: str,
               url: str,
               returncode: int,
               output: str,
               err: str):
        """
        Print result of url request
        """

        if returncode != 0 or ("error" in output) or len(err) > 0:
            print(url,
                  data,
                  returncode,
                  output,
                  err)
            return weechat.WEECHAT_RC_ERROR
        return weechat.WEECHAT_RC_OK

    def shutdown(self):
        """
        Shutdown
        """

        print("shutdown invoked")
        return weechat.WEECHAT_RC_OK


weenotifier: WeeNotifier | None = None


def message_cb(data: str,
               buffer: str,
               date: int,
               tags: list[str],
               displayed: int,
               highlight: int,
               prefix: str,
               message: str):
    """
    Message callback by weechat-C-api.
    """

    if weenotifier is not None:
        return weenotifier.message(data,
                                   buffer,
                                   date,
                                   tags,
                                   displayed,
                                   highlight,
                                   prefix,
                                   message)
    return weechat.WEECHAT_RC_ERROR


def result_cb(data: str,
              url: str,
              returncode: int,
              output: str,
              err: str):
    """
    Result callback by weechat-C-api
    """

    if weenotifier is not None:
        return weenotifier.result(data,
                                  url,
                                  returncode,
                                  output,
                                  err)
    return weechat.WEECHAT_RC_ERROR


def shutdown_cb():
    """
    Shutdown callback by weechat-C-api
    """

    if weenotifier is not None:
        return weenotifier.shutdown()
    return weechat.WEECHAT_RC_ERROR


def main():
    global weenotifier
    weenotifier = WeeNotifier()


if __name__ == "__main__":
    main()
