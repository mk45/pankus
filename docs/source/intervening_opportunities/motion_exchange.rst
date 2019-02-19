.. _motion_exchange_function:

motion_exchange
==================

Data used
----------

.. toctree::
  :maxdepth: 1
  :caption: Tables:

  ../tables/motion_exchange
  ../tables/motion_exchange_fraction
  ../tables/ring
  ../tables/ring_total
  ../tables/model_parameters


Effect
------
- :ref:`motion_exchange_fraction_table` and :ref:`motion_exchange_table` tables are created and written.
- Motion exchange is comuted according to intervening opportunities model or with convolution model if proper convolution parameters are provided.
- Fraction of motion exchange for an origin/destination point is set to be the fraction of arriving motions to the area's ring multiplied by ratio of destinations in the area to number of destinations in the whole ring where area is located.

