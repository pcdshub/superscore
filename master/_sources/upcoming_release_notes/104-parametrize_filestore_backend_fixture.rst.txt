104 parametrize filestore backend fixture
#################

API Breaks
----------
- the filestore_backend fixture requires parametrization using 'db/filestore.json' to match prior behaviour
- the linac_data fixture returns a Root rather than a tuple of Entries
- the comparison_linac_snapshot fixture has been renamed, and returns a Root containing the entries from linac_data in addition to its comparison snapshot

Features
--------
- make the filestore_backend fixture accept pytest parametrized args
- args can be a file path, functions that return a Root or Iterable[Entry], or function names resolvable in conftest.py

Bugfixes
--------
- N/A

Maintenance
-----------
- N/A

Contributors
------------
- shilorigins
