.. superscore documentation master file, created by
   sphinx-quickstart on Tue May 22 13:13:05 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to superscore's documentation!
===========================================================

Disclaimer
^^^^^^^^^^
Superscore is still in beta.  Features are still in development, and bugs may
have slipped through.  If you have feedback, we would very much appreciate you
leaving a issue in our `github repository <https://github.com/pcdshub/superscore>`_


Introduction
^^^^^^^^^^^^
Superscore is an EPICS PV configuration management application that aims to be
searchable and flexible.  Superscore features a centralized data model, multiple
communication layers (CA, PVA), a python client, and a Graphical User Interface.
The goal is to provide users a the ability to snapshot the state of their system
and restore known good states.  Central to the design of this application is enabling
users to specify what groups of PVs they want to store, and organize them in a sensible
way.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api.rst
   releases.rst
   upcoming_changes.rst

.. toctree::
   :maxdepth: 1
   :caption: Links
   :hidden:

   Github Repository <https://github.com/pcdshub/superscore>



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
