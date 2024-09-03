77 mnt_snap_ro_readback
#######################

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
- Adjusts Client.snap so that if a `Parameter` in a `Collection` is marked as
  read_only=True, it should be captured as a `Readback` in the corresponding `Snapshot`.

Contributors
------------
- tangkong
