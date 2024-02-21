95 gui_entry_pages
##################

API Breaks
----------
- N/A

Features
--------
- Adds BaseParameterPage, which dynamically shows/hides edit widgets based on which fields are present.  This page widget is designed for Single PV entries.
- Adds BusyCursorThread, for showing a busy cursor during potentially blocking work.
- Adds first pass at Nestible (Collection, Snapshot) view pages.

Bugfixes
--------
- N/A

Maintenance
-----------
- Modifies the signature of open_page_slot to pass the client through

Contributors
------------
- tangkong
