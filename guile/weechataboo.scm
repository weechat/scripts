; WeeChat-Script to replace emotion-tags with random emoticons.
; Copyright (C) 2017 Alvar <post@0x21.biz>
;
; This program is free software: you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation, either version 3 of the License, or
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
; For usage see `/help weechataboo`

(use-modules (srfi srfi-1))

; -> List
; Returns a list of available emotions.
(define (emotion-categories)
  (string-split (weechat:config_get_plugin "emotions") #\,))

; String -> String
; Returns an emoticon for a known emotion.
(define (emotion->emoticon emo)
  (let
    ((emotions (string-split (weechat:config_get_plugin emo) #\,))
     (random-emotion (lambda (l)
                       (list-ref l (random (length l))))))
    (random-emotion emotions)))

; String -> String
; Replaces in the given string every ~~EMOTION with a fitting emoticon.
(define (emoticonize-line line)
  (let*
    ((as-tag (lambda (emo) (string-append "~~" emo)))
     (has-emotions? (lambda (txt)
                      (any (lambda (emo)
                             (number? (string-contains txt (as-tag emo))))
                           (emotion-categories))))
     (replace (lambda (emo txt)
                (let ((pos (string-contains txt (as-tag emo))))
                  (if (number? pos)
                    (string-replace
                      txt (emotion->emoticon emo)
                      pos (+ (string-length (as-tag emo)) pos))
                    txt))))
     (new-line (fold replace line (emotion-categories))))
    (if (has-emotions? new-line)
      (emoticonize-line new-line)
      new-line)))

; Pointer String String -> Weechat-Return 
; This function was registered to be called when an input was submitted and
; will try to replace ~~EMOTIONs to emoticons.
(define (command-run data buffer command)
  (let*
    ((input  (weechat:buffer_get_string buffer "input"))
     (output (emoticonize-line input)))
    (weechat:buffer_set buffer "input" output))
  weechat:WEECHAT_RC_OK)

; Pointer String List -> Weechat-Return
; Function which tells you to RTFM.
(define (weechataboo-func data buffer args)
  (weechat:print "" "See /help weechataboo")
  weechat:WEECHAT_RC_OK)

; -> ()
; Function to be executed when there is no config yet. Creates a dummy one.
(define (initial-setup)
  (let*
    ; Some defaults which may be useful‥
    ((emotions
       '(("angry" "눈_눈,(¬_¬),(｀ε´),(¬▂¬),（▽д▽）")
         ("blush" "(´ω｀*),(‘-’*),(/ε＼*),(*ﾟ∀ﾟ*),(*´ｪ｀*)")
         ("cry"   "（；へ：）,（πーπ）,（ｉДｉ）,(;Д;),(╥_╥)")
         ("dance" "ヾ(^^ゞ),(ノ^o^)ノ,⌎⌈╹우╹⌉⌍,└|ﾟεﾟ|┐,┌|ﾟзﾟ|┘,(〜￣△￣)〜")
         ("drink" "(＾-＾)＿日,(*^◇^)_旦,(　 ゜Д゜)⊃旦,~~旦_(-ω-｀｡)")
         ("excited" "(≧∇≦*),ヽ(＾Д＾)ﾉ,(* >ω<)")
         ("gross" "（咒）,( ≖ิ‿≖ิ ),ʅ(◔౪◔ ) ʃ")
         ("happy" "≖‿≖,（＾ω＾）,(＾ω＾),ヽ(ヅ)ノ,(¬‿¬)")
         ("heart" "♡＾▽＾♡,✿♥‿♥✿,(｡♥‿♥｡),ヽ(o♡o)/")
         ("hug"   "⊂(・﹏・⊂),(っ´▽｀)っ,(づ￣ ³￣)づ,⊂(´・ω・｀⊂)")
         ("kiss"  "|°з°|,（*＾3＾）,(´ε｀*)")
         ("lenny" "( ͡ ͜ʖ ͡ ),( ͡~ ͜ʖ ͡°),( ͡~ ͜ʖ ͡~),ヽ( ͝° ͜ʖ͡°)ﾉ,(つ ͡° ͜ʖ ͡°)つ")
         ("magic" "(っ・ω・）っ≡≡≡≡≡≡☆,ヽ༼ຈل͜ຈ༽⊃─☆*:・ﾟ")
         ("sheep" "@^ェ^@,@・ェ・@")
         ("shrug" "┐(´д｀)┌,╮(╯∀╰)╭,┐(´∀｀)┌,ʅ(́◡◝)ʃ,ヽ(~～~ )ノ")
         ("shock" "(ﾟдﾟ；)")
         ("shy"   "(/ω＼),(‘-’*),(´～｀ヾ),(〃´∀｀)")
         ("smug"  "(￣ω￣),(￣ー￣),（￣ー￣）,(^～^)")
         ("wink"  "ヾ(＾∇＾),ヾ(☆▽☆),(。-ω-)ﾉ,( ･ω･)ﾉ")))
     (names (string-join (map car emotions) ",")))
    (and
      (weechat:config_set_plugin "emotions" names)
      (for-each
        (lambda (emo)
          (weechat:config_set_plugin (car emo) (cadr emo)))
        emotions))))

; -> Weechat-Return
; Function to be called when the plugin is unloaded. Will hopefully clean
; up all settings.
(define (clean-up)
  (for-each weechat:config_unset_plugin (emotion-categories))
  (weechat:config_unset_plugin "emotions")
  weechat:WEECHAT_RC_OK)


(weechat:register
  "weechataboo" "Alvar" "0.1" "GPL3"
  "Replace emotion-tags with random emoticons" "clean-up" "")

(and (eq? (weechat:config_is_set_plugin "emotions") 0)
     (initial-setup))

(weechat:hook_command_run "/input return" "command-run" "")
(weechat:hook_command
  "weechataboo"
  (string-append "This script automatically replaces written emotion-keywords\n"
                 "with a random emoticon from a list of matching ones. The\n"
                 "keyword must have two tildes (~~) as a prefix.\n"
                 "Example: ~~wink\n\n"
                 "All values are comma separated. Please make sure that every\n"
                 "emotion in the `emotions`-list has its own entry!\n\n"
                 "→ Keywords: /set plugins.var.guile.weechataboo.emotions\n"
                 "→ Emoticons: /set plugins.var.guile.weechataboo.$EMOTION\n")
  "" "" "" "weechataboo-func" "")
