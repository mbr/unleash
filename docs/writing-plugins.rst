Writing plugins
===============


Logging and progress output
---------------------------

Unleash supports different output levels, named after regular loglevels:
``debug``, ``verbose``, ``normal`` and ``quiet``. Plugins need not know about
these as the logger takes care of only displaying messages that are required.
The following guidelines for output should be kept in mind regardless:

* For every large step performed (that is, roughly once per plugin), output a
  single ``info``-level log message. These are displayed during normal
  operation and allow the user to follow what is happening.
* Warnings and errors should be output using the issue collector (they will
  trigger a log entry automatically) and, if possible, contain a suggested
  possible fix.
* You can output any number of helpful debug or trace messages on the ``debug``
  log level.
