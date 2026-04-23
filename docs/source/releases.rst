

v0.1.0 (2026-04-22)
===================
This is the initial beta release of superscore.  The items here are a simple
record of the contributions made.

API Breaks
----------
- Client._build_snapshot optionally accepts an empty Snapshot to fill instead of creating a new one
- :meth:`superscore.backends.filestore.FilestoreBackend.__init__` does not accept ``initialize`` arg
- :meth:`FilestoreBackend.store` does not accept any args
- the filestore_backend fixture requires parametrization using 'db/filestore.json' to match prior behaviour
- the linac_data fixture returns a Root rather than a tuple of Entries
- the comparison_linac_snapshot fixture has been renamed, and returns a Root containing the entries from linac_data in addition to its comparison snapshot
- Client.search takes SearchTerms as ``*args`` rather than key-value pairs as ``**kwargs``

Features
--------
- Adds ability to import/export from serialized json
- Enable/disable Entry page save button based on Validation status, providing helpful tooltips
- ability to save Snapshots for a Collection
- Extends ``EpicsData`` fields to include controls metadata
- Support editing for LivePVTableModel and NestableModel
- Adds ``ValueDelegate``, which provides an edit delegate based on the datatype of the cell
- add button to take new snapshots on NestablePage
- implement fixture for running IOCs that can be queried for integration tests
- implement module that can run IOCs for demos
- Add skeleton for Client and Backend base class
- Adds DirectoryBackend, which stores serialized Entry's in a nested directory structure (Radix Tree)
- Adds main window widget and cli entrypoint skeleton
- Add "ancestor" search option, returning entries reachable from the ancestor
- Add custom exceptions: BackendError, FileExistsError, FileNotFoundError
- Add TestBackend: an in-memory backend for testing purposes
- Add LINAC Collection test fixture
- Add batch restore functionality to RestoreDialog
- Adds CollectionBuilderPage, which can add/remove PVs/Collections
- Adds FilterComboBox, for filtering through options
- Adds BaseParameterPage, which dynamically shows/hides edit widgets based on which fields are present.  This page widget is designed for Single PV entries.
- Adds BusyCursorThread, for showing a busy cursor during potentially blocking work.
- Adds first pass at Nestible (Collection, Snapshot) view pages.
- Adds DiffPage for comparing two Entry's with diff highlighting
- Adds FilestoreBackend
- Adds Root for holding top-level Entry objects
- Adds UUID to potentially lazy fields
- Adds DataWidget, RootModel, and related qt helpers
- adds templating support, with GUI support
- adds ``Window.open_page(entry)`` for opening an ``Entry`` in a new tab
- Adds icons to represent various ``Entry`` subclasses
- ``demo`` subcommand that launches the UI with a backend and IOC populated with PV
  data from selectable fixtures
- ``ui.py::main`` accepts an existing `Client` as an arg
- Add dataclasses and simple serialization tests
- Adds ability for Client to search for configuration files, and load settings from them.
- Adds top-level tree to main window
- Adds icons to the TreeModel
- Adds fill_uuid method to TreeModel, which grabs data from client if possible
- Adds context menu on tree view for accessing custom actions.
- add restore page: shows all non-Nestable Entries within a Snapshot, can compare to live data
- restore page can be opened through the tree view context menu
- middle clicking on a BaseDataTableView cell copies the contents to the clipboard
- double clicking a TreeView item opens the detailed Entry page
- Implements :meth:`Client.apply` method for writing values from :class:`Entry` data to the control system.
- Adds ``BaseTableEntryModel``, from which ``LivePVTableModel`` and ``NestableTableModel`` inherit.
  These table models are intended to display ``Entry`` data and be reused across the application.
- Implements ``LivePVTableModel``, including polling behavior for live PV display.
- Add validation methods to Entry and all subclasses
- Vendors the exception handler from PyDM and install it in the main GUI
- Added an :meth:`_Backend.is_writable()` method for determining if a given entry can be written to.
  - For :class:`FilestoreBackend` this is always `True` (if you can write to the file)
  - For :class:`DirectoryBackend` this depends on the particular file (normally `True`)
  - For :class:`TestBackend` this is always `True`
- :class:`Client` now refers to the writability of an entry before trying to save/update it
- :class:`Client` can now be set to disallow writing to entries that already existed in the database before the session started.
- set up a recently-modified-entry cache held in Client memory to keep track of entries added in the current session, so users can continue to edit them
- Adds :meth:`Nestable.walk_children` to assist in finding all recently edited Entries and their children
- Adds shim layer for aioca (async Channel Access)
- Adds ControlLayer class for communicating with shims
- make the filestore_backend fixture accept pytest parametrized args
- args can be a file path, functions that return a Root or Iterable[Entry], or function names resolvable in conftest.py
- add RestorePage table tooltips with PV name, status, and severity
- add working restore button and dialog to RestorePage
- Standardize data handling to create and expect EpicsData instead of backend-specific data types.
- regex search on Entry text fields
- filter Entrys by tag
- filter Entrys by attribute value
- Adds SearchPage for filtering and viewing Entry objects
- Adds EntryDiff, which tracks two Entrys, along with a list of DiffItem objects
- Implements Client.fill for filling Nestable Entry UUID fields
- Implements Client.compare

Bugfixes
--------
- Main window closes tab widget tabs when closed, so they can do their clean up
- Assign readback dataclasses based on parent class.  Previously :class:`ParameterPage` was
  assigning a :class:`Readback` to :meth:`Parameter.readback` instead of a :class:`Parameter` as defined in the data model
- Fixes bug where TestBackend could not delete an entry that was a direct child of the :class:`Root`
- Fixes behavior of FilestoreBackend to throw :class:`EntryError` exceptions rather than just returning None
- _Backend.get -> _Backend.get_entry in Client._build_snapshot
- add mandatory 3rd arg in setattr in FilestoreBackend.fill_uuids
- store EpicsData.data as primitive type, so it displays properly when returned by a Qt model
- don't change control_layer/core.py:SHIMS when creating dummy CLs
- Properly fill items in the the shared tree view (:class:`RootTree`)
- Fix bug where clicking the "add PV" button would also add a collection if it had been added before
- Properly check for sub-collections that have already been added during collection building
- Add newline to end of file when writing filestore json
- Fills the top-level entry whenever RootTree model is created, to ensure at least first level of children display
- Flatten and cache entries in FilestoreBackend.save_entry
- Refreshes window whenever a new collection is added from the :class:`CollectionBuilderPage`
- ``_root`` was ``None`` during :class:`FilestoreBackend` file initialization, causing ``TypeError``
- :meth:`IOCFactory.prepare_attrs` now strips attr names of all non-alphanumeric characters
- Adjusts :meth:`RootTree.canFetchMore` to check both the dataclass and the ``EntryItem`` to avoid uuid-filling desyncs
- Fixes incorrect argument specification in open_page_slot
- stop LivePVTableModel polling before clearing data, to avoid accessing deleted data
- Fill UUID children when found in LivePVTableView and NestableTableView
- Keep track of dirty status in qt models, and send signals when this changes
- Grab fresh Entry from uuid whenever opening a page

Maintenance
-----------
- Refactors validation methods to pass a ValidationResult (holding validation state and reasoning) instead of simple boolean
- Allow :meth:`Window.open_page` to open uuids that exist in the database
- generalized Client._gather_data to work on any type of Entry
- made Client._gather_data iterative rather than recursive to simplify the conditional logic
- autoupdate pre-commit config
- Refactors common models to come with their own views, to improve user friendliness
- Adds ``test_data``, ``test_backend``, and ``test_client`` fixtures that can be parametrized, replacing other specialized fixtures that maybe setup.
- Adds :func:`setup_test_stack` to concisely parametrize and request the aforementioned ``test_*`` fixtures.
- Organizes data-helper functions into a separate ``conftest_data`` file.
- Adjusts existing tests to use ``setup_test_stack`` and ``test_*`` fixtures instead of other specialized fixtures.
- adds WindowLinker.get_window() so WindowLinkers can do more with the Window outside of dedicated methods
- define linac testing structure outside of fixture
- Adds the restore button to SnapshotPage
- Makes DataWidget use Generics to appease type hinting complaints
- Adjusts Client.snap so that if a :class:`Parameter` in a :class:`Collection` is marked as
  read_only=True, it should be captured as a :class:`Readback` in the corresponding :class:`Snapshot`.
- Adjust :meth:`Client.fill` to allow us to specify fill depth
- Move :meth:`FilestoreBackend.compare` upstream into :class:`_Backend`
- Implement ``.search`` and ``.root`` in :class:`TestBackend` for completeness
- Updates dependencies, adds pre-release notes framework
- Adds common RootTreeView which holds the RootTree model.  Upstreams standard settings and context menu support
- ControlLayer._get_single: return CommunicationError rather than propagating
- Move heavier imports in subcommands to separate file, allowing CLI to load them on demand rather than every time.
- Document that _Backend.delete_entry raises error when entry is out-of-sync with backend
- Document that _Backend.get_entry raises error when entry can't be found
- Modifies the signature of open_page_slot to pass the client through
- Refactors context menu generation, applying it to all common views
- Adds a QtSingleton class for singleton QObject subclasses that want to hold singleton signals
- Set up backend fixtures, sample database, and sample database
- Make Setpoint and Readback into direct Entry subclasses for ease of serialization
- adjust tree views to set data in-place, rather than re-creating the model
- Improve UUID / str interchangeability
- Replaces :func:`populate_backend` to help enable "superscore demo" cli
- Adds basic test coverage for command line interface
- Makes Window a QtSingleton, and adds an access function for use throughout superscore ui widgets
  Uses this singleton to access methods that were passed around manually in the past as optional arguments or set attributes (open_page_slot, client)
- increase main windows's default size
- adds some debug statements and properly initialize logging
- Adjusts :class:`TaskStatus` use to properly capture exceptions.
- Add Snapshot test fixture mirroring the LINAC Collection
- Introduce Nestable class interface
- use signals and slots to coordinate RestorePage table live data display status
- add second linac snapshot, and include in demo config
- Adjust Status, Severity enums to start at 0, matching EPICS
- Refactor tests to be much more thorough about dirty status checking
- Allow relative paths for backend filestore location
- Adjust FilestoreBackend search method to permit some special arguments and special search types.

Contributors
------------
- shilorigins
- tangkong
