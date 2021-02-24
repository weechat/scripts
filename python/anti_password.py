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
# (requires WeeChat ≥ 0.4.0).
#
# History:
#
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
SCRIPT_VERSION = '1.0'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC = 'Prevent a password from being accidentally sent to a buffer'

# script options
ap_settings_default = {
    'password_condition': (
        # default value
        '${words} == 1 && ${lower} >= 1 && ${upper} >= 1 && ${digits} >= 1 '
        '&& ${special} >= 1',
        # help text
        'condition evaluated to check if the input string is a password; '
        'allowed variables: '
        '${words} = number of words, '
        '${lower} = number of lower case letters, '
        '${upper} = number of upper case letters, '
        '${digits} = number of digits, '
        '${special} = number of other chars (not letter/digits/spaces), ',
    ),
}
ap_settings = {}


def ap_config_cb(data, option, value):
    """Called when a script option is changed."""
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in ap_settings:
            ap_settings[name] = value
    return weechat.WEECHAT_RC_OK


def ap_input_return_cb(data, buf, command):
    """Callback called when Return key is pressed in a buffer."""
    input_text = weechat.buffer_get_string(buf, "input")
    if not weechat.string_input_for_buffer(input_text):
        # commands are ignored
        return weechat.WEECHAT_RC_OK

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

    if ret == '1':
        # password detected, do NOT send it to the buffer!
        return weechat.WEECHAT_RC_OK_EAT

    # not a password
    return weechat.WEECHAT_RC_OK


def main():
    """Main function."""
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
        # set default settings
        for option, value in ap_settings_default.items():
            if weechat.config_is_set_plugin(option):
                ap_settings[option] = weechat.config_get_plugin(option)
            else:
                weechat.config_set_plugin(option, value[0])
                ap_settings[option] = value[0]
            weechat.config_set_desc_plugin(
                option,
                '%s (default: "%s")' % (value[1], value[0]))

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME,
                            'ap_config_cb', '')

        # hook Return key
        weechat.hook_command_run('/input return', 'ap_input_return_cb', '')


if __name__ == '__main__' and IMPORT_OK:
    main()
