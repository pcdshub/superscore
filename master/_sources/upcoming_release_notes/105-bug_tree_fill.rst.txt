105 bug_tree_fill
#################

API Breaks
----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- Properly fill items in the the shared tree view (`RootTree`)

Maintenance
-----------
- Adjust `Client.fill` to allow us to specify fill depth
- Move `FilestoreBackend.compare` upstream into `_Backend`
- Implement `.search` and `.root` in `TestBackend` for completeness

Contributors
------------
- tangkong
