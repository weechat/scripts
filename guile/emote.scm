; Copyright (c) 2014 by csmith <caleb.smithnc@gmail.com>
;
; This program is free software; you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation; either version 3 of the License, or
; (at your option) any later version.
;
; This program is distributed in the hope that it will be useful,
; but WITHOUT ANY WARRANTY; without even the implied warranty of
; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
; GNU General Public License for more details.
;
; You should have received a copy of the GNU General Public License
; along with this program.  If not, see <http://www.gnu.org/licenses/>.
;
;
; (this script requires WeeChat 0.4.1 or newer)
;
; History:
; 2017-02-18, nycatelos <nycatelos@riseup.net>
;   version 0.3: added more emotes
; 2016-06-03, nycatelos <nycatelos@riseup.net>
;   version 0.2: added additional emotes
; 2014-05-03, csmith <caleb.smithnc@gmail.com>
;   version 0.1: initial release

(use-modules (srfi srfi-69))

(weechat:register "emote" "Caleb Smith" "0.3" "GPL" "Emote" "" "")

; Mappings of words with their emoticons
(define patterns (alist->hash-table '(
    ("tableflip" . "(╯° °）╯︵ ┻━┻)")
    ("rageflip" . "(ノಠ益ಠ)ノ彡┻━┻")
    ("doubleflip" . "┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻")
    ("disapproval" . "ಠ_ಠ")
    ("sun" . "☼")
    ("kitaa" . "キタ━━━(゜∀゜)━━━!!!!!")
    ("joy" . "◕‿◕")
    ("nyancat" . "~=[,,_,,]:3")
    ("lenny" . "( ͡° ͜ʖ ͡°)")
    ("shrug" . "¯\\_(ツ)_/¯")
    ("denko" . "(・ω・)")
    ("tableplace" . "┬─┬ ノ( ゜-゜ノ)")
    ("gface" . "( ≖‿≖)")
    ("facepalm" . "(－‸ლ)")
    ("tehe" . "☆~(◡﹏◕✿)")
    ("angry" . "(╬ ಠ益ಠ)")
    ("umu" . "(￣ー￣)")
    ("toast" . "（ ^_^）o自自o（^_^ ）")
    ("yay" . "ヽ(´ー｀)ﾉ")

)))


; Derive the tab completion string for the subcommands.
(define tab-completions
    (apply string-append
        (map (lambda (i) (string-append "|| " i))
            (hash-table-keys patterns))))


; Hook main function up to the /emote command
(weechat:hook_command
    "emote" "Emote" "/emote phrase"
    (string-append
        ""
        "\nUse `/emote phrase`. Words in phrase will be replaced with their"
        "\nemoticons:"
        "\n"
        "\nExamples:"
        "\n    /emote tableflip - (╯° °）╯︵ ┻━┻)"
        "\n    /emote look - ಠ_ಠ")
    tab-completions
    "main" "")


; Handle the IRC command given by the user. Sets input buffer as a side-effect
(define (main data buffer command)
    (weechat:buffer_set buffer "input"
        (apply string-append (map (lambda (c)
            (string-append (hash-table-ref/default patterns c c) " "))
            (string-tokenize command))))
    weechat:WEECHAT_RC_OK)
