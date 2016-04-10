; Copyright (c) 2014 by msoucy <msoucy@csh.rit.edu>
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

(weechat:register "karmastorm" "Matt Soucy" "0.3" "GPL3" "KarmaStorm" "" "")

; Hook main function up to the /emote command
(weechat:hook_command
  "karmastorm" "Karma Storm" "/karmastorm num names..."
  "Increment karma for the given names"
  "" "main" "")

; Increments karma for all users provided
(define (main data buffer command)
  (letrec ((toked (string-tokenize command))
           (incr (lambda (n)
                   (weechat:command buffer (string-append n "++"))))
           (lp (lambda (num)
                 (if (not (zero? num))
                   (begin
                     (map incr (cdr toked))
                     (lp (- num 1)) ))))
           (err (lambda ()
                  ((weechat:print "" "Expected arguments for karmastorm")))))
    (if (null? toked) err (lp (string->number (car toked)))))
  weechat:WEECHAT_RC_OK)
