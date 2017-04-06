;; -*- geiser-scheme-implementation: 'guile -*-
;; Copyright 2017 by Zephyr Pellerin <zv@nxvr.org>
;; ------------------------------------------------------------
;; This program is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation; either version 3 of the License, or
;; (at your option) any later version.
;;
;; This program is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.
;;
;; You should have received a copy of the GNU General Public License
;; along with this program.  If not, see <http://www.gnu.org/licenses/>.

;; History:
;; 1.2 - Use weechat plugin configuration data to match IRC gateways
;; 0.9 - Lookup correct servername in /VERSION
;; 0.8 - Barebones, contained list of translations

(use-modules ((srfi srfi-1)
              #:select (any fold)))
(use-modules ((srfi srfi-26)
              #:select (cut)))
(use-modules (ice-9 regex))
(use-modules (ice-9 hash-table))
(use-modules (ice-9 match))

(define *weechat/script-name* "gateway_rename")
(define *weechat/script-author* "zv <zv@nxvr.org>")
(define *weechat/script-version* "1.2.1")
(define *weechat/script-license* "GPL3")
(define *weechat/script-description* "Convert usernames of gateway connections their real names")


;; A test-harness for checking if we are inside weechat
(define-syntax if-weechat
  (syntax-rules ()
    ((_ conseq alt) (if (defined? 'weechat:register) conseq alt))
    ((_ conseq) (if (defined? 'weechat:register) conseq))))

(if-weechat
 (weechat:register *weechat/script-name*
                   *weechat/script-author*
                   *weechat/script-version*
                   *weechat/script-license*
                   *weechat/script-description*
                   "" ""))

;; `user-prefix' is a distinguishing username prefix for 'fake' users
(define *user-prefix* "^")
(define *gateway-config* "gateways")
(define *default-irc-gateways* "(freenode #radare r2tg <NICK>) (freenode #test-channel zv-test NICK:)")

(define (print . msgs)
  (if (defined? 'weechat:print)
      (weechat:print "" (apply format (cons #f msgs)))))

;; A regular expression must have the gateway username in the first matchgroup,
;; the "real" username in the 3rd, and the real-username along with it's enclosing
;; brackets in the 2nd
(define *gateway-regexps* (make-hash-table))

(define (process-network-infolist)
  "Convert the internal user-defined servername to the 'true' servername
returned during /version"
  (define il (weechat:infolist_get "irc_server" "" ""))

  ;; pull the network field out of the list of /VERSION results
  (define (extract-network result)
    (if (null? result) #f
        (match (string-split (car result) #\=)
          [("NETWORK" network) network]
          [_ (extract-network (cdr result))])))

  ;; pull out a '(name network-name) pair from an infolist str
  (define (process return-code)
    (if (= return-code 0) '()
        (let* ((name      (weechat:infolist_string il "name"))
               (isupport  (weechat:infolist_string il "isupport"))
               (reply     (string-split isupport #\space))
               (network   (or (extract-network reply)
                              ;; if no network, use local name
                              name)))
          (cons
           (cons name network)
           (process (weechat:infolist_next il))))))

  (process (weechat:infolist_next il)))

;; This is a table that maps a weechat network 'name' to it's IRC-style hostname
(define *hostname-table* (alist->hash-table '(("freenode" . "freenode"))))
(if-weechat
 (set! *hostname-table* (alist->hash-table (process-network-infolist))))

(define (replace-privmsg msg gateways)
  "A function to replace the PRIVMSG sent by by a gateway "
  (let* ((match? (cut regexp-exec <> msg))
         (result (any match? gateways)))
    (if result
        (let* ([nth-match (cut match:substring result <>)]
               ;; take everything after username before message
               [username (nth-match 1)]
               [real-username (nth-match 3)]
               ;; Extract everything after the gateway-user mask
               [raw-message (string-copy msg
                                     (match:end result 2)
                                     (string-length msg))]
               ;; .. and be sure to strip any preceding characters
               [message (string-trim raw-message)]
               ;; extract everything before the message but after the username
               [hostmask (string-copy msg
                                      (match:end result 1)
                                      (match:start result 2))])
          (string-append ":" *user-prefix* real-username hostmask message))
        msg)))

(define (server->gateways server)
  (hash-ref *gateway-regexps* (hash-ref *hostname-table* server)))

(define (privmsg-modifier data modifier-type server msg)
  "The hook for all PRIVMSGs in Weechat"
  (let ((gateways (server->gateways server)))
    (if gateways
        (replace-privmsg msg gateways)
        msg)))

(define* (make-gateway-regexp gateway-nick channel mask #:optional emit-string)
  "Build a regular expression that will match the nick, channel and \"<NICK>\"-style mask"
  (let* ([mask-regexp ;; replace <NICK> with <(\\S*?)>
          (regexp-substitute/global #f "NICK" mask 'pre "(\\S*?)" 'post "")]
         [composed-str (format #f
                               ":(~a)!\\S* PRIVMSG ~a :(~a)"
                               gateway-nick
                               (if (equal? "*" channel) "\\S*" channel)
                               mask-regexp)])
    (if emit-string composed-str (make-regexp composed-str))))

(define (extract-gateway-fields str)
  "This is a hack around Guile's non-greedy matchers.

  # Example
  scheme@(guile-user)> (extract-gateway-fields \"(freenode #radare r2tg <NICK>)\")
  $1 = (\"freenode\" \"#radare\" \"r2tg\" \"<NICK>\")"
  (let* ((range-end  (λ (range) (+ 1 (cdr range))))
         (find-space (λ (end) (string-index str #\space end)))
         ;; opening (first) and closing (last) parenthesis
         (opening-par   (string-index str #\())
         (closing-par   (string-index str #\)))
         ;; extract the range of each
         (server        (cons (+ 1 opening-par) (find-space 0)))
         (channel       (cons (range-end server) (find-space (range-end server))))
         (gateway-nick  (cons (range-end channel) (find-space (range-end channel))))
         (mask          (cons (range-end gateway-nick) closing-par)))

    ;; and then get the strings
    (map (λ (window) (substring str (car window) (cdr window)))
         (list server channel gateway-nick mask))))

(define* (process-weechat-option opt #:optional emit-string)
  "Takes in the application-define weechat-options and emits a server and
matching regular expression.

The optional parameter `emit-string' controls if a string or a compiled regular
expression is returned.

# Example

scheme@(guile-user)> (process-weechat-option \"(freenode #radare r2tg <NICK>)\")
$1 = '(\"freenode\" . (make-regexp \":(r2tg)!\\S* PRIVMSG #radare :(<(\\S*?)>) .*\")))"
  (let* ((fields (extract-gateway-fields opt))
         (server  (list-ref fields 0))
         (channel (list-ref fields 1))
         (gateway-nick (list-ref fields 2))
         (mask    (list-ref fields 3)))
    (cons server (make-gateway-regexp gateway-nick channel mask emit-string))))


(define (split-gateways config)
  "Push our elts onto the stack to extract our configs

# Example
scheme@(guile-user)> (split-gateways \"(freenode #radare r2tg <NICK>)(* * slack-irc-bot NICK:)\")
$1 = (\"(freenode #radare r2tg <NICK>)\" \"(* * slack-irc-bot NICK:)\")
"
  (define (process stk current rest)
    (if (string-null? rest) (cons current '())
        (let* ((head (string-ref rest 0))
               (nrest (string-drop rest 1))
               (ncurrent (string-append current (string head))))
          (cond
           [(and (null? stk) (not (string-null? current)))
            (cons current (process stk "" rest))]
           [(eq? head #\() (process (cons #\( stk) ncurrent nrest)]
           [(eq? head #\)) (process (cdr stk) ncurrent nrest)]
           ;; skip characters if our stk is empty
           [(null? stk) (process stk current nrest)]
           [else (process stk ncurrent nrest)]))))

  (process '() "" config))

(define (fetch-weechat-gateway-config)
  "Extract the gateway configuration string"
  (if-weechat (weechat:config_get_plugin *gateway-config*)
              *default-irc-gateways*))

(define (assign-gateways-regex)
  "Fetch our weechat gateway configuration and assign it to our local regexps"
  (let* ((config_str (fetch-weechat-gateway-config))
         (config_lst (split-gateways config_str))
         (gateways   (map process-weechat-option config_lst)))
    ;; for each gateway, add it to our `*gateway-regexps*' ht
    (for-each
     (λ (gt)
       (let* ((server    (car gt))
              (new-regex (cdr gt))
              (server-regexps (hash-ref *gateway-regexps* server '())))
         (hash-set! *gateway-regexps* server
                    (cons new-regex server-regexps))))
     gateways)))

;; Initialize our weechat settings & privmsg hook
(define (renamer_command_cb data buffer args) weechat::WEECHAT_RC_OK)

(if-weechat
 (begin
   (if (not (= 1 (weechat:config_is_set_plugin *gateway-config*)))
       (weechat:config_set_plugin
        *gateway-config*
        *default-irc-gateways*))

   (weechat:hook_modifier "irc_in_privmsg" "privmsg-modifier" "")

   (weechat:hook_command *weechat/script-name*
                         *weechat/script-description*
                         "" ;; arguments
                         "
There are many IRC gateway programs that, rather than sending as if they were
another user, simply prepend the name of the user that is using that gateway to
the messages they are sending.

For example: `slack-irc-bot` might send a message to #weechat:

    slack-irc-bot: <zv> How about them Yankees?

gateway_rename intercepts that message and converts it to:

    ^zv: How about them Yankees?

(gateway_rename prefixes the `^' (caret) symbol to each message to prevent message spoofing)

Adding a Renamer:

  Which servers, channels, users and nickname templates are renamed can all be
  modified in `plugins.var.guile.gateway_rename.gateways'

  Two gateways are matched by default, but are primarily intended to serve as a
  template for you to add others.

  Each gateway renamer is placed inside of a set of parenthesis and contain four fields respectively:
  1. IRC server name (use the same name that weechat uses)
  2. Channel
  3. Gateway's nick/user name
  4. The last field is a template for how to match the nickname of the 'real user'
     For example, if you wanted to convert the message 'gateway-bot: zv: Yes' into 'zv: Yes'
     You would set the last field to 'NICK:' because each NICK at the beginning of the message is suffixed with a `:'
                         "
                         ""
                         "renamer_command_cb"
                         "")))

;; Setup our gateways->regex map
(assign-gateways-regex)

;;(print "Gateway Nickconverter by zv <zv@nxvr.org>")
