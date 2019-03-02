Installation instructions
=========================

.. contents::

Some things you will need before installing OpenWorkouts
--------------------------------------------------------

1. Python_: The Python programming language, version 3.x (it has been tested
   with versions >= 3.5).

2. `Google Chrome`_ + chromedriver_: This is not a requirement in order to run
   OpenWorkouts, but without it, for workouts that have gps tracking data, you
   won't get a nice map displaying your route in the workouts lists (you will
   see the map in the details page though).

   We use Chrome to render a static image out of the route map.

   .. note::

      chromedriver_ is usually bundled with Chrome, so installing chrome
      will install chromedriver too, but in some systems (MacOS for example)
      you will have to install it separately.

   .. note::

      (If you prefer you can use Chromium_ instead of Chrome)


The easiest way, using the installer
------------------------------------

This is the easiest way to install OpenWorkouts on any unix-like system (like
Linux, any BSD-based system or MacOS).

Grab a copy of the sources, either from https://openworkouts directly or from
the `github releases page`_.

Uncompress the tarball or zipped file (depending on what you did download)

Run the installer, in a shell/console::

  ./bin/install

This script will take all the needed steps to set everything up for you.


Setting it all up manually
--------------------------

**TBW**


.. _Python: https://python.org
.. _`Google Chrome`: https://www.google.com/chrome
.. _Chromium: https://www.chromium.org/Home
.. _chromedriver: https://chromedriver.chromium.org
.. _`github releases page`: https://github.com/openworkouts/OpenWorkouts/releases
