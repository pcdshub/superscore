94 snapshot restore page
#################

API Breaks
----------
- N/A

Features
--------
- add restore page: shows non-Nestable Entries within a Snapshot, can compare to live data
- restore page is associated with opening a Snapshot, and can be opened through the tree view
- middle clicking on a BaseDataTableView cell copies the contents to the clipboard

Bugfixes
--------
- stop LivePVTableModel polling before clearing data, to avoid accessing deleted data

Maintenance
-----------
- increase main windows's default size

Contributors
------------
- shilorigins
