---
name: Add/update a script
about: Add or update a script in repository
title: "script_name.py X.Y: …"

---

## Script info

<!-- MANDATORY INFO: -->

- Script name: 
- Version: 

<!-- Optional: external dependencies -->
- Requirements: 

<!-- Optional: fill only if you are sure that a specific WeeChat version is required -->
- Min WeeChat version: 

<!-- Optional: tags for script (see list of tags on https://weechat.org/scripts/), new tags are allowed -->
- Script tags: 

## Description

<!-- Describe the new script or your changes in a few sentences -->



## Checklist (new script)

<!-- To fill only if you are adding a new script -->

<!-- Please check each item with "[x]" and ensure your new script is compliant -->
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

## Checklist (script update)

<!-- To fill only if you are updating an existing script -->

<!-- Please check each item with "[x]" and ensure the script is compliant -->
<!-- See file Contributing.md for more information -->

- [ ] Author has been contacted
- [ ] Single commit, single file added
- [ ] Commit message format: `script_name.py X.Y: …`
- [ ] Script version and Changelog have been updated
- [ ] For Python script: works with Python 3 (Python 2 support is optional)
