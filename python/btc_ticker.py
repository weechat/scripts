#!/usr/bin/env python
# coding=utf-8

# Copyright (c) 2014, 2017 Eugene Ciurana (pr3d4t0r)
# All rights reserved.
#
# Version 1.2.0
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
# * Neither the name of the {organization} nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Main repository, version history:  https://github.com/pr3d4t0r/weechat-btc-ticker
#
# Version history:  https://github.com/pr3d4t0r/weechat-btc-ticker


from time import gmtime, strftime

import json

import weechat


# *** constants ***

BTCE_API_TIME_OUT = 15000 # ms
BTCE_API_URI      = 'url:https://btc-e.com/api/2/%s_%s/ticker'

DEFAULT_CRYPTO_CURRENCY = 'btc'
DEFAULT_FIAT_CURRENCY   = 'usd'

VALID_CRYPTO_CURRENCIES = [ DEFAULT_CRYPTO_CURRENCY, 'ltc', 'eth' ]
VALID_FIAT_CURRENCIES   = [ DEFAULT_FIAT_CURRENCY, 'eur', 'rur' ]

COMMAND_NICK = 'tick'


# *** Functions ***

def extractRelevantInfoFrom(rawTicker):
    payload = json.loads(rawTicker)
    result  = dict()

    for key in payload['ticker']:
        result[key] = payload['ticker'][key]

    result['updated'] = unicode(payload['ticker']['updated'])
    result['time']    = strftime('%Y-%b-%d %H:%M:%S Z', gmtime(payload['ticker']['updated']))

    return result


def display(buffer, ticker, currencyLabel, fiatCurrencyLabel):
    output = ('%s:%s sell = %4.2f, buy = %4.2f, last = %4.2f; high = %4.2f, low = %4.2f, avg = %4.2f  ||  via BTC-e on %s' % \
                    (currencyLabel, fiatCurrencyLabel, \
                    ticker['sell'], ticker['buy'], ticker['last'], \
                    ticker['high'], ticker['low'], ticker['avg'], \
                    ticker['time']))

    weechat.command(buffer, '/say %s' % output)


def displayCurrentTicker(buffer, rawTicker, cryptoCurrency, fiatCurrency, serviceURI):
    if rawTicker:
        ticker = extractRelevantInfoFrom(rawTicker)
        display(buffer, ticker, cryptoCurrency.upper(), fiatCurrency.upper())
    else:
        weechat.prnt(buffer, '%s\t*** UNABLE TO READ DATA FROM:  %s ***' % (COMMAND_NICK, serviceURI))


def tickerPayloadHandler(tickerData, service, returnCode, out, err):
    if returnCode == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt(u"", u"%s\tError with service call '%s'" % (COMMAND_NICK, service))
        return weechat.WEECHAT_RC_OK

    tickerInfo = tickerData.split(' ')
    displayCurrentTicker('', out, tickerInfo[0], tickerInfo[1])

    return weechat.WEECHAT_RC_OK


def fetchJSONTickerFor(cryptoCurrency, fiatCurrency):
    serviceURI = BTCE_API_URI % (cryptoCurrency, fiatCurrency)
    tickerData = cryptoCurrency+' '+fiatCurrency

    weechat.hook_process(serviceURI, BTCE_API_TIME_OUT, 'tickerPayloadHandler', tickerData)


def displayCryptoCurrencyTicker(data, buffer, arguments):
    cryptoCurrency = DEFAULT_CRYPTO_CURRENCY
    fiatCurrency   = DEFAULT_FIAT_CURRENCY

    if len(arguments):
        tickerArguments = arguments.split(' ') # no argparse module; these aren't CLI, but WeeChat's arguments

        if len(tickerArguments) >= 1:
            if tickerArguments[0].lower() in VALID_CRYPTO_CURRENCIES:
                cryptoCurrency = tickerArguments[0].lower()
            else:
                weechat.prnt(buffer, '%s\tInvalid crypto currency; using default %s' % (COMMAND_NICK, DEFAULT_CRYPTO_CURRENCY))

        if len(tickerArguments) == 2:
            if tickerArguments[1].lower() in VALID_FIAT_CURRENCIES:
                fiatCurrency = tickerArguments[1].lower()
            else:
                weechat.prnt(buffer, '%s\tInvalid fiat currency; using default %s' % (COMMAND_NICK, DEFAULT_FIAT_CURRENCY))

    fetchJSONTickerFor(cryptoCurrency, fiatCurrency)

    return weechat.WEECHAT_RC_OK


# *** main ***

weechat.register('btc_ticker', 'pr3d4t0r', '1.2.0', 'BSD', 'Display a crypto currency spot price ticker (BTC, LTC) in the active buffer', '', 'UTF-8')

weechat.hook_command(COMMAND_NICK, 'Display common crypto currency spot exchange values conveted to fiat currencies like USD or EUR',\
            '[btc|ltc|nmc [usd|eur|rur] ]', '    btc = Bitcoin\n    ltc = Litecoin\n    eth = Ethereum\n    nmc = Namecoin\n    usd = US dollar\n    eur = euro\n    rur = Russian ruble', '', 'displayCryptoCurrencyTicker', '')
