# Copyright (c) 2021 Simon Ser <contact@emersion.fr>
#
# License: GNU Affero General Public License version 3
# https://www.gnu.org/licenses/agpl-3.0.en.html

import weechat

weechat.register("soju", "soju", "0.1.3", "AGPL3", "soju bouncer integration", "", "")

bouncer_cap = "soju.im/bouncer-networks"
caps_option = weechat.config_get("irc.server_default.capabilities")
caps = weechat.config_string(caps_option)
if bouncer_cap not in caps:
    if caps != "":
        caps += ","
    caps += bouncer_cap
    weechat.config_option_set(caps_option, caps, 1)

main_server = None
added_networks = {}

def handle_isupport_end_msg(data, signal, signal_data):
    global main_server

    server_name = signal.split(",")[0]
    netid = weechat.info_get("irc_server_isupport_value", server_name + ",BOUNCER_NETID")

    if netid != "":
        added_networks[netid] = True

    hdata = weechat.hdata_get("irc_server")
    server_list = weechat.hdata_get_list(hdata, "irc_servers")
    server = weechat.hdata_search(hdata, server_list, "${irc_server.name} == " + server_name, 1)
    cap_list = weechat.hdata_hashtable(hdata, server, "cap_list")
    if not bouncer_cap in cap_list:
        return weechat.WEECHAT_RC_OK

    if main_server is not None:
        return weechat.WEECHAT_RC_OK
    main_server = server_name

    weechat.command(weechat.buffer_search("irc", "server." + server_name), "/quote BOUNCER LISTNETWORKS")

    return weechat.WEECHAT_RC_OK

def handle_bouncer_msg(data, signal, signal_data):
    server_name = signal.split(",")[0]
    msg = weechat.info_get_hashtable("irc_message_parse", { "message": signal_data })

    args = msg["arguments"].split(" ")
    if args[0] != "NETWORK":
        return weechat.WEECHAT_RC_OK

    # Don't connect twice to the same network
    netid = args[1]
    if netid in added_networks:
        return weechat.WEECHAT_RC_OK_EAT

    # Retrieve the network name from the attributes
    net_name = None
    raw_attr_list = args[2].split(";")
    for raw_attr in raw_attr_list:
        k, v = raw_attr.split("=")
        if k == "name":
            net_name = v
            break

    check_char = lambda ch: ch.isalnum() or ch in ".-_"
    net_name = "".join(ch if check_char(ch) else "_" for ch in net_name)

    addr = weechat.config_string(weechat.config_get("irc.server." + server_name + ".addresses"))
    username = weechat.config_string(weechat.config_get("irc.server." + server_name + ".username"))
    if "/" in username:
        username = username.split("/")[0]
    add_server = [
        "/server",
        "add",
        net_name,
        addr,
        "-temp",
        "-ssl",
        "-username=" + username + "/" + net_name,
    ]

    for k in ["password", "sasl_mechanism", "sasl_username", "sasl_password"]:
        v = weechat.config_string(weechat.config_get("irc.server." + server_name + "." + k))
        add_server.append("-" + k + "=" + v)

    weechat.command(weechat.buffer_search("core", "weechat"), " ".join(add_server))
    weechat.command(weechat.buffer_search("core", "weechat"), "/connect " + net_name)

    return weechat.WEECHAT_RC_OK_EAT

weechat.hook_signal("*,irc_raw_in_376", "handle_isupport_end_msg", "") # RPL_ENDOFMOTD
weechat.hook_signal("*,irc_raw_in_422", "handle_isupport_end_msg", "") # ERR_NOMOTD
weechat.hook_signal("*,irc_raw_in_bouncer", "handle_bouncer_msg", "")
