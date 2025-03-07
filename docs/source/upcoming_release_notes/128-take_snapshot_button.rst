128 take snapshot button
#################

API Breaks
----------
- Client._build_snapshot optionally accepts an empty Snapshot to fill instead of creating a new one

Features
--------
- add button to take new snapshots on NestablePage

Bugfixes
--------
- _Backend.get -> _Backend.get_entry in Client._build_snapshot
- add mandatory 3rd arg in setattr in FilestoreBackend.fill_uuids
- store EpicsData.data as primitive type, so it displays properly when returned by a Qt model

Maintenance
-----------
- adds WindowLinker.get_window() so WindowLinkers can do more with the Window outside of dedicated methods

Contributors
------------
- shilorigins
