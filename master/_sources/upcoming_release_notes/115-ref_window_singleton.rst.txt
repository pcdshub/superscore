115 ref_window_singleton
########################

API Breaks
----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- N/A

Maintenance
-----------
- Makes Window a QtSingleton, and adds an access function for use throughout superscore ui widgets
  Uses this singleton to access methods that were passed around manually in the past as optional arguments or set attributes (open_page_slot, client)

Contributors
------------
- tangkong
