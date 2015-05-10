How unleash works
=================

Unleash has a defined model of the release process. This section documents it
to ease the development of new plugins:


Git based
---------

Unleash is tied to the concept of a distributed version control system, in
practice this is strictly git_ right now. Development happens as usual, until a
developer decides to cut a release.

.. _git: https://git-scm.com


Cutting a release
-----------------

Cutting a release means designating a single *candidate commit* to be the basis
for a new release. It is not used directly as the release, but rather forms the
basis for the *release commit*. The *release commit* is a commit that has had
its development-specific information removed (for example, a version number
might change from ``0.6.dev1`` to ``0.6``) and afterwards gets tagged with the
release number.

The release process happens in distinct steps:

1. The **collect_info** phase. Unleash gathers required information in this
   step that is used later on.
2. During the **prepare_release** phase, the *release commit* is created.
3. Afterwards, a **lint_release** is performed on the *release commit*. This
   will check the resulting new commit for errors and warnings.
4. During the **prepare_dev** phase, a new development commit. This usually
   just means bumping the version number to the next ``.dev``-version.
4. If everything went fine, these commits (which existed only in memory up
   until this point) are added to the repository. unleash will also update
   branches when it is safe to do so.


Release a release
-----------------

The release action consists of two steps:

1. The **collect_info** step, which is the same as during the release process.
2. The **publish_release** step, which performs actual actions.



Python 3 support
----------------

unleash relies heavily on dulwich and therefore only supports Python 2. This
restriction only applies to running unleash, it handles release of packages
written in Python 3 just fine.

