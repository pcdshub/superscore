148 bug_setData_dirty
#####################

API Breaks
----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- Keep track of dirty status in qt models, and send signals when this changes
- Grab fresh Entry from uuid whenever opening a page

Maintenance
-----------
- Refactor tests to be much more thorough about dirty status checking

Contributors
------------
- tangkong
