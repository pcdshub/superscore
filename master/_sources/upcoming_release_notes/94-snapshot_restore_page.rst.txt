94 snapshot restore page
#################

API Breaks
----------
- N/A

Features
--------
- add restore page: shows all non-Nestable Entries within a Snapshot, can compare to live data
- restore page can be opened through the tree view context menu
- middle clicking on a BaseDataTableView cell copies the contents to the clipboard
- double clicking a TreeView item opens the detailed Entry page

Bugfixes
--------
- stop LivePVTableModel polling before clearing data, to avoid accessing deleted data

Maintenance
-----------
- increase main windows's default size

Contributors
------------
- shilorigins
