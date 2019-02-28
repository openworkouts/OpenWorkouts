OpenWorkouts Changelog
======================

.. contents::


Release summary
---------------

0.2.0, March 1, 2019:
       Improvements on user signup, added i18n support for the UI (+ es
       translations)

0.1.0, February 15, 2019:
       Initial release, includes signup/login + per-user complete workout
       management and an initial set of stats.

Release details
---------------

0.2.0
+++++

- New:

  - Added support for different locale/language for the UI (#56, #69)
    (+ spanish translations)

  - Added user verification by email on signup (#29, #61, #66, #67)

  - Several internal improvements:

    - Added migrations support for the ZODB database (#45)

    - Moved the setup of development environments to use ZEO

    - Added a tasks module to run periodic tasks into separate processes

    - Set logging capabilities and proper log files

- Fixes:

  - Fixed bug in the profile page yearly stats chart, that caused the wrong
    weekly/monthly label to be highlighted on page reload.

  - Weeks for the current month were displayed in the wrong part of
    the yearly activity chart in the profile page (#68)

  - Set a title automatically when adding manually a workout without providing
    one (#58)

  - Signup form does not keep values on error (#60)

  - Profile images were too big (#51)

  - Fixed several UI problems in mobile devices (#50, #57)

  - Fixed broken *bin/install* script (+ extended it with some new features)

  - Use a gif "loading" image instead of a fixed image while the screenshot
    of a workout tracking map is being generated

0.1.0
+++++

- New:

  - User signup and login, password reset and basic user profile management

  - Multi-sport workouts support

    - Add workouts manually or upload using tracking files (gpx and fit
      supported)

    - Edit/update workouts manually or with tracking files

  - Time-based archive for workouts in the user dashboard

  - Time-based (global, per-month, per-week) stats and charts

  - Detailed view of a workout, including basic workout info, stats and
    an interactive map for those workouts with gps data
