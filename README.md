# WeeChat official scripts

These official scripts can be installed with command `/script install <name>`
in WeeChat.

They are also displayed on http://weechat.org/scripts/

## Add a script

To submit a new script in this repository, please use the form at:
http://weechat.org/scripts/add/

There are strict rules for new scripts, please read them carefully, otherwise
your script will be rejected.

Pending scripts are visible at: http://weechat.org/scripts/pending/

## Update a script

There are two ways to send a new release for a script:

* send a pull request
* use the form at: http://weechat.org/scripts/update/

When sending a new version :

* don't forget to update the version number in the script (used in `register`
  function)
* if the script is tagged `py3k-ok` (script running fine with Python 3.x),
  please ensure that your update is still compatible with both
  Python 2.x **AND** 3.x.
