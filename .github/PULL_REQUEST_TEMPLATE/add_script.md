---
name: Add a script
about: Add a new script in repository
title: "script_name.py X.Y: fix..."
labels: new script

---

## Script info

<!-- MANDATORY INFO: -->

- Script name: 
- Version: 
- License: 

<!-- Optional: external dependencies -->
- Requirements: 

<!-- Optional: fill only if you are sure that a specific WeeChat version is required -->
- Min WeeChat version: 

<!-- Optional: tags for script (see list of tags on https://weechat.org/scripts/), new tags are allowed -->
- Script tags: 

## Description

<!-- Describe the script in a few sentences -->



## Checklist

<!-- Please check each item with "[x]" and ensure your script is compliant -->
<!-- See file Contributing.md for more information -->

- [ ] Single commit, single file added
- [ ] Commit message: `New script name.py: short description…`
- [ ] No similar script already exists
- [ ] Name: max 32 chars, only lower case letters, digits and underscores
- [ ] Unique name, does not already exist in repository
- [ ] No shebang on the first line
- [ ] Comment in script with name/pseudo, e-mail and license
- [ ] Only English in code/comments
- [ ] Pure WeeChat API used, no extra API
- [ ] Function `hook_process` is used for blocking calls
- [ ] For Python script: works with Python 3 (Python 2 support is optional)
