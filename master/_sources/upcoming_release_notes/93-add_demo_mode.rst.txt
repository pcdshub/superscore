93 add demo mode
#################

API Breaks
----------
- `FilestoreBackend.__init__` does not accept `initialize` arg
- `FilestoreBackend.store` does not accept any args

Features
--------
- `demo` subcommand that launches the UI with a backend and IOC populated with PV
  data from selectable fixtures
- `ui.py::main` accepts an existing `Client` as an arg

Bugfixes
--------
- `_root` was `None` during `FilestoreBackend` file initialization, causing `TypeError`
- `IOCFactory.prepare_attrs` now strips attr names of all non-alphanumeric characters

Maintenance
-----------
- Improve UUID / str interchangeability

Contributors
------------
- shilorigins
