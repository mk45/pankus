.. _logged_function:

logged_function
====================

Data used
----------

.. toctree::
  :maxdepth: 1
  :caption: Tables:

  ../tables/model_log

Effect
------
- table :ref:`model_log_table` is created and/or written with action (function completed with list of its parameters), its id, id of a parent action, time of execution and version of pankus
- ``logged_function`` function is written as a wrapper to make documenting functions user friendly
- ``logged_function`` stores executed functions and their parameters
