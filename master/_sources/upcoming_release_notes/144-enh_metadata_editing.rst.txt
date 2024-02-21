144 enh_metadata_editing
########################

API Breaks
----------
- N/A

Features
--------
- Vendors the exception handler from PyDM and install it in the main GUI
- Added an `_Backend.is_writable()` method for determining if a given entry can be written to.

  - For `FilestoreBackend` this is always `True` (if you can write to the file)
  - For `DirectoryBackend` this depends on the particular file (normally `True`)
  - For `TestBackend` this is always `True`

- `Client` now refers to the writability of an entry before trying to save/update it
- `Client` can now be set to disallow writing to entries that already existed in the database before the session started.
- set up a recently-modified-entry cache held in Client memory to keep track of entries added in the current session, so users can continue to edit them
- Adds `Nestable.walk_children()` to assist in finding all recently edited Entries and their children

Bugfixes
--------
- N/A

Maintenance
-----------
- N/A

Contributors
------------
- tangkong
