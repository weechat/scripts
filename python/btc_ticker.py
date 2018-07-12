#!/usr/bin/env python
# coding=utf-8

# Copyright (c) 2014-2018 Eugene Ciurana (pr3d4t0r)
# All rights reserved.
#
# Version - see _VERSION global
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


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime

import json

import weechat


# *** constants ***

CRYPTOCUR_API_TIME_OUT  = 15000 # ms
CRYPTOCUR_API_URI       = 'url:https://api.cryptonator.com/api/ticker/%s-%s'
DEFAULT_CRYPTO_CURRENCY = 'btc'
DEFAULT_FIAT_CURRENCY   = 'usd'

VALID_CRYPTO_CURRENCIES = [ DEFAULT_CRYPTO_CURRENCY, 'eth', 'bch', 'xrp', 'xem', 'ltc', 'dash', 'neo', 'etc', ]
VALID_FIAT_CURRENCIES   = [ DEFAULT_FIAT_CURRENCY, 'eur', 'rur', ]
_VERSION                = '2.1.0'

COMMAND_NICK = 'tick'


# *** Functions ***

def extractRelevantInfoFrom(rawTicker):
    payload = json.loads(rawTicker)
    result  = payload['ticker']

    return result


def display(buffer, ticker):
    baseCurrency   = ticker['base']
    targetCurrency = ticker['target']
    price          = float(ticker['price'])
    volume         = float(ticker['volume'])
    change         = float(ticker['change'])
    now            = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    output = '%s:%s price = %5.2f, volume = %5.2f, change = %4.2f on %s' % (
                baseCurrency,
                targetCurrency,
                price,
                volume,
                change,
                now)

    weechat.command(buffer, '/say %s' % output)


def displayCurrentTicker(buffer, rawTicker):
    if rawTicker:
        ticker = extractRelevantInfoFrom(rawTicker)
        display(buffer, ticker)
    else:
        weechat.prnt(buffer, '%s\t*** UNABLE TO READ DATA FROM:  %s ***' % (COMMAND_NICK, CRYPTOCUR_API_URI))


def tickerPayloadHandler(_, service, returnCode, out, err):
    if returnCode == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt("", "%s\tError with service call '%s'" % (COMMAND_NICK, service))
        return weechat.WEECHAT_RC_OK

    displayCurrentTicker('', out)

    return weechat.WEECHAT_RC_OK


def fetchJSONTickerFor(cryptoCurrency, fiatCurrency):
    serviceURI = CRYPTOCUR_API_URI % (cryptoCurrency, fiatCurrency)

    weechat.hook_process(serviceURI, CRYPTOCUR_API_TIME_OUT, 'tickerPayloadHandler', "")


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

weechat.register('btc_ticker', 'pr3d4t0r', _VERSION, 'BSD', 'Display a crypto currency spot price ticker (BTC, ETH, LTC) in the active buffer', '', 'UTF-8')

cryptoCurrencies = '|'.join(sorted(VALID_CRYPTO_CURRENCIES))
fiatCurrencies   = '|'.join(VALID_FIAT_CURRENCIES)
argsWeeChat      = '[%s [%s] ]' % (cryptoCurrencies, fiatCurrencies)

weechat.hook_command(COMMAND_NICK, 'Display common crypto currency spot exchange values conveted to fiat currencies like USD or EUR',\
            argsWeeChat, '    btc  = Bitcoin\n    eth  = Ethereum\n    bch  = Bitcoin Cash\n    xrp  = Ripple\n    xem  = NEM\n    ltc  = Litecoin\n    dash = Dash\n    neo  = NEO\n    etc  = Ethereum Classic\n\n    usd = US dollar\n    eur = euro\n    rur = Russian ruble', '', 'displayCryptoCurrencyTicker', '')

