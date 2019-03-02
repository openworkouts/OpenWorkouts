Development, how to contribute
==============================

.. contents::


What you need
-------------

Apart from the dependencies described in the doc:install:, you will need:

1. git_. We use it for the version control of OpenWorkouts.

2. lessc_. We use it for writing modular css code (and generate the definitive
   css files for OpenWorkouts)


How to access the source code
-----------------------------

Main development site
+++++++++++++++++++++

OpenWorkouts development is tracked in our trac_ site:

https://openworkouts.org/trac

which is publicly available for everybody.

From there you can browse the sources within your web browser, get a copy
and access all the development information (tasks, bug reports, milestones,
etc).

If you want to get an account and collaborate, get in touch with us at
info@openworkouts.org.

Github mirror
+++++++++++++

We also have a mirror in Github:

https://github.com/openworkouts/OpenWorkouts

Changes made to the OpenWorkouts repositories are populated to Github, so you
can grab a copy of the sources from there too (and fork, make pull requests,
etc).

What we don't have replicated in Github is all the development information
(tasks, bugs, etc).


Development workflow
--------------------

We are using the well-known `git-flow`_ workflow, with some notes:

1. The **master** branch is used to keep track of releases

2. The **current** branch is the branch that keeps the main development
   flow/current.

3. Each time a developer wants to implement a new feature, first the
   developer grabs the ticket(s) related to that feature in trac, then
   a new branch is created from the **current** branch. Work is done on
   that branch, which will be merged back to the **current** branch when
   it has been finished.

   (more info about this workflow in `this tutorial`_, just remember we
   use **current** instead of **development** for the main development
   branch)

4. Features are grouped in **milestones**, which can be viewed in trac:

   https://openworkouts.org/trac/roadmap

   Once all tasks/tickets in a milestone are done, a release branch is
   created. OpenWorkouts is then fully tested, no more features can be
   merged at that time, only bugfixes go into the tree, under that branch.

   When testing has finished, the release branch is then merged into the
   **master** branch, that branch is tagged and a release is done

**Bug reports** are saved into a special milestone:

https://openworkouts.org/trac/milestone/Bug%20reports

When a bug is reported, a developer grabs the ticket containing the bug,
checking which version is affected.

If it affects only a specific version, a hotfix branch for that version is
created (using tags to create a branch from the specific release tag) and
the bugfix is written there.

If it affects all (or several) versions, then the bugfix is developed in a
hotfix branch from current, then it is backported to the previous releases.

**Again**, reading `this tutorial`_ will help you get a better picture of
this workflow (and in case of any questions, just ping us at
info@openworkouts.org)


Documentation
-------------

Docs are built using sphinx_, written in rst_ and they are located within the
**docs/** directory of the main OpenWorkouts repo.


.. _git: https://git-scm.com
.. _lessc: http://lesscss.org
.. _trac: https://trac.edgewall.org
.. _`git-flow`: https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow
.. _`this tutorial`: https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow
.. _sphinx: http://www.sphinx-doc.org/en/master
.. _rst: http://docutils.sourceforge.net/rst.html
