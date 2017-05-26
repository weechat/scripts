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
# 2017-04-19, butlerx
#   Version 1.0.1: remove + from message
# 2017-04-18, butlerx
#   Version 1.0.0: initial version
#

import requests
import weechat

SCRIPT_NAME = "giphy"
SCRIPT_AUTHOR = "butlerx <butlerx@redbrick.dcu.ie>"
SCRIPT_VERSION = "1.0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Insert giphy gif"

URL = "http://api.giphy.com/v1/gifs/"
API = "&api_key=dc6zaTOxFJmzC"
RANDOM = "random?tag=%s"
TRANSLATE = "translate?s=%s"
SEARCH = "search?limit=1&q=%s"


def giphy(data, buf, args):
    """ Parse args to decide what api to use """
    search_string = args.split()
    arg = search_string.pop(0)
    search_string = "+".join(search_string)
    if arg == "search":
        image_url = search(URL + SEARCH + API, search_string)
    elif arg == "msg":
        image_url = translate(URL + TRANSLATE + API, search_string)
    elif arg == "random":
        image_url = random(URL + RANDOM + API, search_string)
    else:
        search_string = arg + "+" + search_string
        image_url = random(URL + RANDOM + API, search_string)
    weechat.command(buf, "giphy %s -- %s" %
                    (search_string.replace("+", " ").strip(), image_url))
    return weechat.WEECHAT_RC_OK


def translate(api, search_term):
    """Query giphy translate api for search"""
    response = requests.get(api % search_term)
    data = response.json()
    try:
        # Translate
        image_url = data["data"]["images"]["original"]["url"]
    except TypeError:
        image_url = "No GIF good enough"
    return image_url


def random(api, search_term):
    """Query giphy random api for search"""
    response = requests.get(api % search_term)
    data = response.json()
    try:
        # Random
        image_url = data["data"]["image_url"]
    except TypeError:
        image_url = "No GIF good enough"
    return image_url


def search(api, search_term):
    """Query giphy search api for search"""
    response = requests.get(api % search_term)
    data = response.json()
    try:
        image_url = data["data"][0]["images"]["original"]["url"]
    except TypeError:
        image_url = "No GIF good enough"
    return image_url


if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        weechat.hook_command("giphy", "Insert a giphy GIF", "",
                             "", "", "giphy", "")
