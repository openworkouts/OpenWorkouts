ZODB migrations
===============

This directory contains the migrations applied to the database when the app
is starting.

.. contents::


Adding a new migration
----------------------

Migrations are named numerically, before adding a new migration look at the
biggest number already available (look at **.py** files), then create a new
**.py** file containing your migration.

For example, if the last migration is **11.py**, create a file called **12.py**
with your migration code inside.

The migration file needs a **migrate** function in it, that accepts one
parameter, the **root** of the pyramid application. There is where your code
should modify whatever needs to be modified in the database.

For example, this migration adds a new attribute to all objects in the
database::

  from BTrees.OOBTree import OOTreeSet

  def migrate(root):
      """
      Adds some_new_attribute to all objects that do not have such attribute

      >>> from models.root import Root, Child
      >>> root = Root()
      >>> child = Child()
      >>> delattr(child, 'some_new_attr')
      >>> assert getattr(child, 'some_new_attr', None) is None
      True
      >>> root.add(child)
      >>> c = root.values()[0]
      >>> assert getattr(c, 'some_new_attr', None) is None
      True
      >>> migrate(root)
      >>> c = root.values()[0]
      >>> assert getattr(c, 'some_new_attr', None) is None
      False
      """
      for child in root.values():
          if getattr(child, 'some_new_attr', None) is None:
              child.some_new_attr = OOTreeSet()


It is important that you add a proper doctest for the migration, because:

1. The first paragraph of the migration will be shown on the app logs, letting
   us known which kind of changes have been made to the database on start.

2. Doctests there allow us to keep code coverage high and test those migrations
   separately

**Please use previous migrations for reference when in doubt on how to write
a new migration**
