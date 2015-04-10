Concepts
========

Unleash has a defined model of the release process. This section documents it
to ease the development of new plugins:


Git based
---------

Unleash is tied to the concept of a distributed version control system, in
practice this is strictly git_ right now. Development happens as usual, until a
developer decides to cut a release.


Cutting a release
-----------------

Cutting a release means designating a single *candidate commit* to be the basis
for a new release. It is not used directly as the release, but rather forms the
basis for the *release commit*. The *release commit* is a commit that has had
its development-specific information removed (for example, a version number
might change from ``0.6.dev1`` to ``0.6``) and afterwards gets tagged with the
release number.

The release process happens in distinct steps:

1. The **info** collection phase. Unleash gathers required information in this
   step that is used in steps further down.
2. During the **release_prep** phase, the *release commit* is created.
3. Afterwards, a **lint** is performed on the *release commit*.
4. Finally the newly prepared and linted committ gets tagged.

.. _git: https://git-scm.com
