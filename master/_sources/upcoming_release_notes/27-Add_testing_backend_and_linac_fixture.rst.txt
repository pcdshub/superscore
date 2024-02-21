27 Add testing backend and linac fixture
#################

API Breaks
----------
- N/A

Features
--------
- Add custom exceptions: BackendError, FileExistsError, FileNotFoundError
- Add TestBackend: an in-memory backend for testing purposes
- Add LINAC Collection test fixture

Bugfixes
--------
- N/A

Maintenance
-----------
- Document that _Backend.delete_entry raises error when entry is out-of-sync with backend
- Document that _Backend.get_entry raises error when entry can't be found

Contributors
------------
- shilorigins
