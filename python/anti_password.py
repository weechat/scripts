#
# Copyright (C) 2021 Sébastien Helleu <flashcode@flashtux.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# Prevent a password from being accidentally sent to a buffer
# (requires WeeChat ≥ 0.4.0 and WeeChat ≥ 3.1 to check secured data).
#
# History:
#
# 2021-03-13, Sébastien Helleu <flashcode@flashtux.org>:
#     version 1.2.1: simplify regex condition
# 2021-03-12, Sébastien Helleu <flashcode@flashtux.org>:
#     version 1.2.0: add option "allowed_regex"
# 2021-02-26, Sébastien Helleu <flashcode@flashtux.org>:
#     version 1.1.0: add options "check_secured_data" and "max_rejects"
# 2021-02-24, Sébastien Helleu <flashcode@flashtux.org>:
#     version 1.0: first official version

"""Anti password script."""

import re

try:
    import weechat
    IMPORT_OK = True
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: https://weechat.org/')
    IMPORT_OK = False

SCRIPT_NAME = 'anti_password'
SCRIPT_AUTHOR = 'Sébastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '1.2.1'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC = 'Prevent a password from being accidentally sent to a buffer'

# script options
ap_settings_default = {
    'allowed_regex': {
        'default': '^(http|https|ftp|file|irc)://',
        'help': (
            'allowed regular expression (case is ignored); this is checked '
            'first: if the input matched this regular expression, it is '
            'considered safe and sent immediately to the buffer; '
            'if empty, nothing specific is allowed'
        ),
    },
    'password_condition': {
        'default': (
            '${words} == 1 && ${lower} >= 1 && ${upper} >= 1 '
            '&& ${digits} >= 1 && ${special} >= 1'
        ),
        'help': (
            'condition evaluated to check if the input string is a password; '
            'allowed variables: '
            '${words} = number of words, '
            '${lower} = number of lower case letters, '
            '${upper} = number of upper case letters, '
            '${digits} = number of digits, '
            '${special} = number of other chars (not letter/digits/spaces), '
        ),
    },
    'check_secured_data': {
        'default': 'equal',
        'help': (
            'consider that all secured data values are passwords and can not '
            'be sent to buffers, possible values: '
            'off = do not check secured data at all, '
            'equal = reject input if stripped input is equal to a secured '
            'data value, '
            'include = reject input if a secured data value is part of input'
        ),
    },
    'max_rejects': {
        'default': '3',
        'help': (
            'max number of rejects for a given input text; if you press Enter '
            'more than N times with exactly the same input, the text is '
            'finally sent to the buffer; '
            'if set to 0, the input is never sent to the buffer when it is '
            'considered harmful (be careful, according to the other settings, '
            'this can completely block the input)'
        ),
    },
}
ap_settings = {}
ap_reject = {
    'input': '',
    'count': 0,
}


def ap_config_cb(data, option, value):
    """Called when a script option is changed."""
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in ap_settings:
            ap_settings[name] = value
    return weechat.WEECHAT_RC_OK


def ap_input_is_secured_data(input_text):
    """Check if input_text is any value of a secured data."""
    check = ap_settings['check_secured_data']
    if check == 'off':
        return False
    sec_data = weechat.info_get_hashtable('secured_data', {}) or {}
    if check == 'include':
        for value in sec_data.values():
            if value and value in input_text:
                return True
    if check == 'equal':
        return input_text.strip() in sec_data.values()
    return False


def ap_input_matches_condition(input_text):
    """Check if input_text matches the password condition."""
    # count chars in the input text
    words = len(list(filter(None, re.split(r'\s+', input_text))))
    lower = sum(1 for c in input_text if c.islower())
    upper = sum(1 for c in input_text if c.isupper())
    digits = sum(1 for c in input_text if c.isdigit())
    special = sum(1 for c in input_text if not (c.isalnum() or c.isspace()))

    # evaluate password condition
    extra_vars = {
        'words': str(words),
        'lower': str(lower),
        'upper': str(upper),
        'digits': str(digits),
        'special': str(special),
    }
    ret = weechat.string_eval_expression(
        ap_settings['password_condition'],
        {},
        extra_vars,
        {'type': 'condition'},
    )
    return ret == '1'


def ap_input_is_password(input_text):
    """Check if input_text looks like a password."""
    return (ap_input_is_secured_data(input_text)
            or ap_input_matches_condition(input_text))


def ap_input_return_cb(data, buf, command):
    """Callback called when Return key is pressed in a buffer."""
    try:
        max_rejects = int(ap_settings['max_rejects'])
    except ValueError:
        max_rejects = 3

    input_text = weechat.buffer_get_string(buf, 'input')

    # check if input is a command
    if not weechat.string_input_for_buffer(input_text):
        # commands are ignored
        ap_reject['input'] = ''
        ap_reject['count'] = 0
        return weechat.WEECHAT_RC_OK

    # check if input matches the allowed regex
    regex = ap_settings['allowed_regex']
    if regex and re.search(regex, input_text, re.IGNORECASE):
        # allowed regex
        ap_reject['input'] = ''
        ap_reject['count'] = 0
        return weechat.WEECHAT_RC_OK

    if ap_input_is_password(input_text):
        if ap_reject['input'] == input_text:
            if ap_reject['count'] >= max_rejects > 0:
                # it looks like a password but send anyway after N rejects
                ap_reject['input'] = ''
                ap_reject['count'] = 0
                return weechat.WEECHAT_RC_OK
            ap_reject['count'] += 1
        else:
            ap_reject['input'] = input_text
            ap_reject['count'] = 1
        # password detected, do NOT send it to the buffer!
        return weechat.WEECHAT_RC_OK_EAT

    # not a password
    ap_reject['input'] = ''
    ap_reject['count'] = 0
    return weechat.WEECHAT_RC_OK


def main():
    """Main function."""
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        # set default settings
        for name, option in ap_settings_default.items():
            if weechat.config_is_set_plugin(name):
                ap_settings[name] = weechat.config_get_plugin(name)
            else:
                weechat.config_set_plugin(name, option['default'])
                ap_settings[name] = option['default']
            weechat.config_set_desc_plugin(
                name,
                '%s (default: "%s")' % (option['help'], option['default']))

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME,
                            'ap_config_cb', '')

        # hook Return key
        weechat.hook_command_run('/input return', 'ap_input_return_cb', '')


if __name__ == '__main__' and IMPORT_OK:
    main()
