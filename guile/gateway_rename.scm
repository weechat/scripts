(use-modules ((srfi srfi-1)
              #:select (any)))
(use-modules ((srfi srfi-26)
              #:select (cut)))
(use-modules (ice-9 regex))
(use-modules (ice-9 hash-table))
(use-modules (ice-9 match))

(if (defined? 'weechat:register)
    (weechat:register "gateway-nickconverter"
                      "zv <zv@nxvr.org>"
                      "1.1"
                      "GPL3"
                      "Convert usernames of gateway connections their real names"
                      ""
                      ""))

;; `user-prefix' is a distinguishing username prefix for 'fake' users
(define *user-prefix* "^")

(define (print . msgs)
  (if (defined? 'weechat:print)
      (weechat:print "" (apply format (cons #f msgs)))))

;; A regular expression must have the gateway username in the first matchgroup,
;; the "real" username in the 3rd, and the real-username along with it's enclosing
;; brackets in the 2nd
(define *gateway-regexps*
  (alist->hash-table
   `(("freenode" .
      (;; r2tg
       ,(make-regexp ":(r2tg)!\\S* PRIVMSG #radare :(<(\\S*?)>) .*")
       ;; slack-irc-bot
       ,(make-regexp ":(slack-irc-bot(1\\|2)?)!\\S* PRIVMSG #\\S* :(<(\\S*?)>) .*")
       ;; test
       ,(make-regexp ":(zv-test)!\\S* PRIVMSG #test-channel :(<(\\S*?)>) .*"))))))

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

(define *hostname-table* (alist->hash-table (process-network-infolist)))

(define (replace-privmsg msg gateways)
  "A function to replace the privmsg sent by by a gateway "
  (let* ((match? (cut regexp-exec <> msg))
         (result (any match? gateways)))
    (if result
        (let* ([nth-match (cut match:substring result <>)]
               ;; take everything after username before message
               [username (nth-match 1)]
               [real-username (nth-match 3)]
               ;; extract everything after the fake r2tg username
               [message (string-copy msg
                                     ;; skip the inserted space
                                     (+ 1 (match:end result 2))
                                     (string-length msg))]
               ;; extract everything before the message but after the username
               [hostmask (string-copy msg
                                      (match:end result 1)
                                      (match:start result 2))])
          (string-append ":" *user-prefix* real-username hostmask message))
        msg)))

(define (server->gateways server)
  (hash-ref *gateway-regexps*
             (hash-ref *hostname-table* server)))

(define (privmsg-modifier data modifier-type server msg)
  ;; fetch the appropriate gateway by server
  (let ((gateways (server->gateways server)))
    (if gateways
        (replace-privmsg msg gateways)
        msg)))

(if (defined? 'weechat:hook_modifier)
    (weechat:hook_modifier "irc_in_privmsg" "privmsg-modifier" ""))

;;(print "Gateway Nickconverter by zv <zv@nxvr.org>")
