SCRIPT_NAME    = "xdccq"
SCRIPT_AUTHOR  = "Randall Flagg <shinigami_flagg@yahoo.it>"
SCRIPT_VERSION = "0.1.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Queue Xdcc messages to bots"

import_ok = True

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

botname = ""
pack = ""
# create a dictionary to save botnames and packs
# botname = {"botname1":"pack1","botname2":"pack2"}
# print myDict["jeff"] # => "jeffs value"
# print myDict.keys() # => ["john", "jeff"]

channel = ""


def xdccq_help_cb(data, buffer, args):
    """Callback for /xdccq command."""
    global botname, pack, channel
    response = {
        'add', 'list', 'listall', 'clear', 'clearall',
    }
    if args:
        words = args.strip().split(' ')
        if words[0] in response:
            if words[0] == "add":
                channel = buffer
                botname = words[1]
                pack = numToList(words[2])
                # look for packs aldready added
                # if already in transfer just add to list
                # else add and start transfer

                # check if bot is in auto accept nicks
                autonicks = weechat.config_string(weechat.config_get("xfer.file.auto_accept_nicks")).split(",")

                if not botname in autonicks:
                    xfer_option = weechat.config_get("xfer.file.auto_accept_nicks")
                    newlist = weechat.config_string(xfer_option)+","+botname

                    rc = weechat.config_option_set(xfer_option, newlist, 1)
                    if rc == weechat.WEECHAT_CONFIG_OPTION_SET_OK_CHANGED:
                        weechat.prnt('', "%s added to xdcc auto-accept list" % botname)
                    elif rc == weechat.WEECHAT_CONFIG_OPTION_SET_OK_SAME_VALUE:
                        weechat.prnt('', "%s already in xdcc auto-accept list" % botname)
                    elif rc == weechat.WEECHAT_CONFIG_OPTION_SET_ERROR:
                        weechat.prnt('', "Error in adding %s in auto-accept list" % botname)
                else:
                    weechat.prnt('', "%s already in xdcc auto-accept nicks, not added." % botname)

                if len(pack):
                    runcommands()
                    pass
            elif words[0] == "list":
                # if botname[words[1]]:
                #     weechat.prnt('',"%s packs left" % botname[words[1]])
                #     weechat.prnt('',"from %s bot" % words[1])
                # else:
                #     weechat.prnt('',"Botname not in queue. Can't list!")
                pass
            elif words[0] == "listall":
                if len(pack):
                    weechat.prnt('', "%s packs left" % pack)
                    weechat.prnt('', "from %s bot" % botname)
                else:
                    weechat.prnt('', "No packs left")
            elif words[0] == "clear":
                # if botname[words[1]]:
                #     del botname[words[1]]
                #     weechat.prnt('',"%s bot queue cleared" % words[1])
                # else:
                #     weechat.prnt('',"Botname not in queue. Can't clear!")
                pass
            elif words[0] == "clearall":
                botname = ""
                pack = ""
                # botname.clear()
                weechat.prnt('', "Queue cleared")
        else:
            weechat.prnt('', "xdccq error: %s not a recognized command. Try /help xdccq" % words[0])

    return weechat.WEECHAT_RC_OK


def numToList(string):
    """Converts a string like '3,5,7-9,14' into a list."""
    ret = []
    numsplit = string.split(",")
    # the following code makes nums into a list of all integers
    for n in numsplit:
        nr = n.split('-')
        # handle the case of a single number
        if len(nr) == 1:
            try:
                ret.append(int(n))
            except:
                raise ValueError("number")
        # handle the case of a range
        elif len(nr) == 2:
            try:
                low = int(nr[0])
                nx = nr[1].split("%", 1)
                if len(nx) == 1:
                    high = int(nr[1]) + 1
                    step = 1
                else:
                    high = int(nx[0]) + 1
                    step = int(nx[1])
                if low > high:
                    raise ValueError("number")
                ret += list(range(low, high, step))
            except ValueError:
                raise ValueError("number")
        else:
            raise ValueError("range")
    return ret


def runcommands():
    global botname, pack, channel
    weechat.prnt('', "Pack %s remaining" % pack)
    if len(pack):
        onepack = pack.pop(0)
        weechat.command(channel, "/msg " + botname + " xdcc send " + str(onepack))
    return weechat.WEECHAT_RC_OK


def xfer_ended_signal_cb(data, signal, signal_data):
    # at the end of transfer print the botname and completed file
    # weechat.infolist_next(signal_data)
    # weechat.prnt('',"%s" % weechat.infolist_string(signal_data, 'remote_nick'))
    runcommands()
    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "")
    weechat.hook_command(
            SCRIPT_NAME, SCRIPT_DESC,
            '\nadd [name] packs\n list\n listall [name]\n clear\n clearall [name]',
            'ADD: adds packs to [botname] queue  \n LIST: list [botname] queue \n Pack format can be 1-10 or 1,2,3 or 1-10,12,15 \n LISTALL: list all queue \n CLEAR: clean all queues \n CLEARALL: clears queue for [botname]',
            'add %(nick) packs'
            ' || list  %(nick)'
            ' || listall'
            ' || clear %(nick)'
            ' || clearall',
            'xdccq_help_cb', '')
    weechat.hook_signal("xfer_ended", "xfer_ended_signal_cb", "")
