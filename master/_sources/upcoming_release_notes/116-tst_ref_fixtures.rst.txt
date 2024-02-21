116 tst_ref_fixtures
####################

API Breaks
----------
- N/A

Features
--------
- N/A

Bugfixes
--------
- Fixes bug where TestBackend could not delete an entry that was a direct child of the `Root`
- Fixes behavior of FilestoreBackend to throw `Entry*Error` exceptions rather than just returning None

Maintenance
-----------
- Adds `test_data`, `test_backend`, and `test_client` fixtures that can be parametrized, replacing other specialized fixtures that maybe setup.
- Adds `setup_test_stack` to concisely parametrize and request the aforementioned `test_*` fixtures.
- Organizes data-helper functions into a separate `conftest_data` file.
- Adjusts existing tests to use `setup_test_stack` and `test_*` fixtures instead of other specialized fixtures.

Contributors
------------
- tangkong
