Developer Documentation
=======================

This is a gathering point for the notes and thoughts of the primary developer as
of April 2026.  I hope to capture some of the thoughts behind
the design decisions made, not to convince others of their correctness but rather
to (hopefully) provide helpful guidance for future developers.

I apologize in advance.

The Architecture
----------------
The application is built around operations using the `Client`.  In order to perform
actions in the application, the `Client` holds references to a "Control Layer"
and a "Backend"

- "Control Layer": Used for communication with the controls system.

  - Currently this include CA, but could be trivially extended to PVA.

- "Backend": Used for communication with the data storage system.

  - Currently we feature two file-based backends, and one in-memory test backend.

By abstracting these interfaces, we make it possible to replace the backing technologies
without redesigning the application.

The GUI communicates entirely with the client, and should not hold any business
logic of its own.  Of course, this line may have been inadvertently blurred during development in
some places, but future developers should strive to maintain this boundary.

To help build a responsive GUI, we have added callbacks to the `Client`.  These
callbacks fire when specific events happen.  These callbacks should not be needed
for programmatic or interactive use of the `Client`.

.. uml:: superscore.client
    :classes:
    :caption: UML Diagram describing the superscore Client


Backend types
^^^^^^^^^^^^^
**`FilestoreBackend`**: Stores Entries in a single file as a JSON blob.  The JSON is generated
via apischema deserialization.  This is the easiest backend to work with for
local development, as changes to the database are easily observed.  This backend
obviously scales poorly with database size.

**`DirectoryBackend`**: Stores Entries in directories based on their uuid.
The directory structure is a `Radix Tree <https://en.wikipedia.org/wiki/Radix_tree>`__
with a default depth of 3.  This schema keeps `Entry` data organized and spread
across multiple files for safety.

Control Layer types
^^^^^^^^^^^^^^^^^^^
**`AiocaShim`**: An EPICS Channel Access communication layer that supports asyncio
access of PVs.   The ``asyncio`` operation is abstracted away from users of the
shim.


How to use the Dataclasses
--------------------------
If one wants to use superscore in other applications, one can manipulate the data
model dataclasses directly in Python, and use the Client to communicate with the
database.

One can simply import the dataclasses and construct the Entry you'd like.

.. code-block:: python

    from superscore.model import Collection, Parameter, Snapshot

    origin_coll = Collection(
        description="origin of various types",
        children=[
            Parameter(pv_name="MY:FLOAT"),
            Parameter(pv_name="MY:INT"),
            Parameter(pv_name="MY:ENUM"),
        ]
    )
    snap = Snapshot(description='various types', title='types collection',
                    origin_collection=origin_coll)
    snap.children.append(Setpoint(pv_name="MY:FLOAT"))
    snap.children.append(Setpoint(pv_name="MY:INT"))
    snap.children.append(Setpoint(pv_name="MY:ENUM"))


Once the `Entry` has been created, `Client` methods can be used to verify and
save the data to the database.


A Primer on the GUI
-------------------
This section is not about how to use the GUI, but rather about the organization
of the code that comprises the GUI.

Main Window Singleton, `WindowLinker`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The GUI centered around the "main window", which holds a tree-view and a tab widget.
The tab widget holds pages that display and edit `Entry` data.  This `Window` is
a singleton that we expose to every widget in the application via the `WindowLinker`
mixin.  This mixin provides methods for accessing the central `Client` and a method
for opening a page (`Window.open_page_slot`).  This mixin should be added to any
page widget opened by the application.


`QDataclassBridge`
^^^^^^^^^^^^^^^^^^
In GUI applications that display the same data across different views, one problem
is keeping the views synchronized when data changes.  While one might expect the
qt MVC framework to help with this, qt models are restricted to the views they service.

One way this is approached in superscore is via the `QDataclassBridge`.  This is
a simple QObject that emits signals when attributes on the dataclass are modified.
This requires changes to the dataclass to be made through the bridge, rather than
directly on the object itself.  (This is a bit obfuscated, and one of the main
drawbacks of the construct).

These bridges are constructed automatically in `DataTracker`


`DataTracker` and `DataWidget`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
`DataWidget` and `DataTracker` are the the primary classes that widgets in the
application inherit from.  Widgets inheriting from `DataWidget` should be initialized
with the dataclass the widget is responsible for.  The `QDataclassBridge` will
be constructed automatically, based on the ``is_independent`` flag.  By default,
each ``DataWidget`` will create a unique bridge for the dataclass it receives.
This is because the application relies on the `Client` as the single source of
truth, and widgets should only update their view if data from the backend has changed.
If ``is_independent`` is False, the `QDataclassBridge` will be created for the
exact instance of the dataclass provided.  This option would be chosen if multiple
`DataWidget` s are being used to construct a single view.
