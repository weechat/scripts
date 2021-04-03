# Contributing to WeeChat scripts

## Adding a new script

New scripts are added with pull requests against master branch of this repository, using the pull request template called `Add script`.

**Important:** please fill the pull request template and follow **all** these rules, otherwise your new script will be rejected:

- pull request:
  - fill the pull request template
  - make only one commit with one new file (the new script) in the appropriate directory, for example `python/` if you add a new Python script
  - use this commit message: `New script name.py: short description of the script…`
- script feature:
  - check that no script or [pending script](https://github.com/weechat/scripts/pulls) does exactly same thing as your script
- script name:
  - use max 32 chars, only lower case letters, digits and underscores
  - use a unique name, not used by any other script, even in a different language
  - use the script name (without extension) in the call to the `register` function
  - do **NOT** use the word "weechat" in the script name: for example prefer `notify.py` to `weechat_notify.py` (the script is only for WeeChat)
- script content:
  - do **NOT** use a shebang on the first line (like `#!/usr/bin/perl`), this is not needed
  - write a comment at the beginning with your name (or pseudo), your e-mail and the chosen license (which must be free)
  - consider using [Semantic versioning ](https://semver.org/) (recommended, not mandatory); only digits and dots are allowed in version
  - use only English for code and comments
  - do **NOT** use an extra API between WeeChat and your script (like Ruby gem "WeeChat"), use the standard WeeChat API only
  - use function [hook_process](https://weechat.org/files/doc/stable/weechat_plugin_api.en.html#_hook_process) or [hook_process_hashtable](https://weechat.org/files/doc/stable/weechat_plugin_api.en.html#_hook_process_hashtable) if your script is doing something blocking (like fetching URL), to not block WeeChat
  - make your Python script compatible with Python 3.x, the support of Python 2.x is now optional
  - use the official WeeChat URL: [https://weechat.org](https://weechat.org) (`https` and no `www.`) in any link to the WeeChat website.

## Updating a script

### Contacting the author

Before updating a script, you **must** contact the author of script directly, and discuss about your changes to check if it's OK, especially if you are adding new features or if you are changing the behavior of the script.

For example, if the author uses a GitHub repository for the script, you can send a pull request to the author instead of sending directly to this repository.\
Then the author will send a pull request on this repository.

### Reporting a vulnerability

Please **DO NOT** file a GitHub issue for security related problems, but send an email to [security@weechat.org](mailto:security@weechat.org) instead.

### Sending the new release

Scripts updates are made with pull requests against master branch of this repository, using the pull request template called `Fix script` or `Improve script`.

**Important:** please fill the pull request template and follow **all** these rules, otherwise your script update will be rejected:

- pull request:
  - fill the pull request template
  - make only one commit on one file in the pull request (the script actually updated)
  - use this commit message: `name.py 1.3: fix some bug…` (`1.3` being the new version of script `name.py`)
- script content:
  - update the version number in the script (used in `register` function) and the ChangeLog, if there is one
  - do **NOT** update the author name in script (used in `register` function), it must always contain the original script author, even if you are doing large updates in the script
  - make any Python script compatible with Python 3.x, the support of Python 2.x is now optional.

## Reporting an issue

Before reporting an issue, it is recommended to contact the author of script directly.\
If you have no answer, or if the author has no time to fix the problem, then you can report the issue in the tracker or send an update of the script if you are able to fix yourself.
