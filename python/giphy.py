# -*- coding: utf-8 -*-
#
# Insert a giphy URL based on a command and search
# Use giphys random, search and translate from weechat
# Usage: /giphy search Search Term
# Usage: /giphy msg message
# Usage: /giphy random Search Term
# Usage: /gipgy Search Term
#
# History:
#
# 2018-10-14, butlerx
#   Version 1.0.2: clean up code
# 2017-04-19, butlerx
#   Version 1.0.1: remove + from message
# 2017-04-18, butlerx
#   Version 1.0.0: initial version
#

from __future__ import absolute_import

from requests import get

from weechat import WEECHAT_RC_OK, command, hook_command, register

SCRIPT_NAME = "giphy"
SCRIPT_AUTHOR = "butlerx <butlerx@redbrick.dcu.ie>"
SCRIPT_VERSION = "1.0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Insert giphy gif"


def giphy(data, buf, args):
    """ Parse args to decide what api to use """
    search_string = args.split()
    arg = search_string.pop(0)
    search_string = "+".join(search_string)
    results = (
        api_request("search", {"limit": 1, "q": search_string})
        if arg == "search"
        else api_request("translate", {"s": search_string})
        if arg == "msg"
        else api_request("random", {"tag": search_string})
        if arg == "random"
        else api_request("random", {"tag": "+".join([arg, search_string])})
    )
    command(
        buf, "giphy {} -- {}".format(search_string.replace("+", " ").strip(), results)
    )
    return WEECHAT_RC_OK


def api_request(method, params):
    """Query giphy api for search"""
    try:
        params["api_key"] = "dc6zaTOxFJmzC"
        response = get("http://api.giphy.com/v1/gifs/{}".format(method), params=params)
        data = response.json()["data"]
        data = data[0] if isinstance(data, list) else data
        return (
            data["images"]["original"]["url"]
            if "image_url" not in data
            else data["image_url"]
        )
    except TypeError:
        return "No GIF good enough"


if __name__ == "__main__":
    if register(
        SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""
    ):
        hook_command(SCRIPT_NAME, SCRIPT_DESC, "", "", "", SCRIPT_NAME, "")
