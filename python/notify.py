# Author: lavaramano <lavaramano AT gmail DOT com>
# This Plugin Calls the libnotify bindings via python when somebody says your nickname, sends you a query, etc.
# To make it work, you may need to download: python-notify (and libnotify - libgtk) 
# TODO: set on/off the notification popup. 
# Released under GNU GPL v2

import weechat, pynotify, string

ICONO_WEECHAT = "/usr/share/pixmaps/weechat.xpm"

weechat.register("wee-n", "0.0.1.5", "", "wee-n!: weechat-notifier :D")
weechat.add_message_handler("privmsg", "hay_mensaje")

class Ween:
    def avisar_usuario(self,canal,mensaje):
        pynotify.init("wee-n")
        wn = pynotify.Notification( canal, mensaje, ICONO_WEECHAT )
        wn.set_urgency(pynotify.URGENCY_NORMAL)
        wn.set_timeout(pynotify.EXPIRES_NEVER)
        wn.show()
            
    def mensaje_irc(self,mensaje):
        cadena = ''
        msg = mensaje.split(":")
        for i in range( len(msg) ):
            if i > 0:
                cadena += msg[i]+' '

        return cadena
            
def hay_mensaje(server, args):
    ween              = Ween()
    cadena            = args.split('!')
    emisor            = cadena[0].replace(':','')
    emisor_dice       = cadena[1].split("PRIVMSG")
    canal             = emisor_dice[1].split(":")[0].strip()
    mensaje           = ween.mensaje_irc( emisor_dice[1] )

    #nicknames - defined in ~/.weechat/weechat.rc
    NICKNAME1 = weechat.get_server_info()[server]['nick1']
    NICKNAME2 = weechat.get_server_info()[server]['nick2']
    NICKNAME3 = weechat.get_server_info()[server]['nick3']

    weechat.prnt( args )

    if (NICKNAME1 == canal) or (NICKNAME2 == canal) or (NICKNAME3 == canal):
        ween.avisar_usuario("Private Window ("+ emisor +")", mensaje )
    elif (NICKNAME1 or NICKNAME2 or NICKNAME3) in mensaje:
        if "ACTION" in mensaje:
            ween.avisar_usuario( "<i>"+mensaje.replace('ACTION','')+"</i>" ,"<b>"+ emisor +" ("+canal+")</b>" )
            weechat.prnt( mensaje )
        else:
            ween.avisar_usuario(canal, "<b>"+emisor+"</b>: "+mensaje )
            
    return weechat.PLUGIN_RC_OK
