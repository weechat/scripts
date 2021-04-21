# Contributing to WeeChat scripts

## Reporting an issue

Before reporting an issue, it is recommended to contact the author of script directly.\
If you have no answer, or if the author has no time to fix the problem, then you can report the issue in the tracker or send an update of the script if you are able to fix yourself.

## Adding a new script

New scripts are added with pull requests against master branch of this repository, using the pull request template called `Add script`.

**Important:** please fill the pull request template and follow **all** these rules, otherwise your new script will be rejected:

- pull request:
  - fill the pull request template
  - make only one commit with one new file (the new script) in the appropriate directory, for example `python/` if you add a new Python script
  - use this commit message: `New script name.py: short description…`
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

Your script is automatically checked in CI, see [Automatic checks on scripts](#automatic-checks-on-scripts).

## Updating a script

### Contacting the author

Before updating a script, if you are not the author of the script, you **must** contact the author of script directly, and discuss about your changes to check if it's OK, especially if you are adding new features or if you are changing the behavior of the script.

For example, if the author uses a GitHub repository for the script, you can send a pull request to the author instead of sending directly to this repository.\
Then the author will send a pull request on this repository.

### Reporting a vulnerability

Please **DO NOT** file a GitHub issue for security related problems, but send an email to [security@weechat.org](mailto:security@weechat.org) instead.

### Sending the new release

Scripts updates are made with pull requests against master branch of this repository, using the pull request template called `Fix script` or `Improve script`.

**Important:** please fill the pull request template and follow **all** these rules, otherwise your script update will be rejected:

- pull request:
  - fill the pull request template
  - make only one commit on one file in the pull request (the script actually updated); exceptions are allowed if motivated in the pull request description
  - use this commit message: `name.py 1.3: fix some bug…` (`1.3` being the new version of script `name.py`)
- script content:
  - update the version number in the script (used in `register` function) and the ChangeLog, if there is one
  - do **NOT** update the author name in script (used in `register` function), it must always contain the original script author, even if you are doing large updates in the script
  - make any Python script compatible with Python 3.x, the support of Python 2.x is now optional.

The script is automatically checked in CI, see [Automatic checks on scripts](#automatic-checks-on-scripts).

## Deleting a script

Deleting a script must be done for a justified decision, for example such reasons are valid:

- the feature implemented by the script has been implemented in WeeChat itself, so the script is no longer of interest
- the web service used by the script has been discontinued, so the script can not work at all any more
- the script uses dependencies that are not maintained any more or subject to vulnerabilities not fixed, thus impacting WeeChat itself.

If you are not the author of the script, you must first contact the author to discuss about the deletion: the author could have a different opinion or could make changes to keep the script.

**Important:** please fill the pull request template and follow **all** these rules, otherwise your script deletion will be rejected:

- pull request:
  - fill the pull request template
  - make only one commit to delete only one script
  - use this commit message: `Remove script name.py`, and it is recommended to explain the reasons in the commit description

## Automatic checks on scripts

Whenever a script is added or updated, the script `weechat-script-lint` is executed by CI in GitHub Actions and looks for errors in the script.

It is recommended to run yourself this script prior to submit the pull request.\
If errors or warnings are detected in the script, you must fix them before the script is manually tested/merged by the WeeChat team.

See the [weechat-script-lint repository](https://github.com/weechat/weechat-script-lint) for more information about the checks performed and how to use the script.
