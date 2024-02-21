72 mnt_common_views
###################

API Breaks
----------
- N/A

Features
--------
- Adds ``BaseTableEntryModel``, from which ``LivePVTableModel`` and ``NestableTableModel`` inherit.
  These table models are intended to display ``Entry`` data and be reused across the application.
- Implements ``LivePVTableModel``, including polling behavior for live PV display.

Bugfixes
--------
- N/A

Maintenance
-----------
- N/A

Contributors
------------
- tangkong
