Unleash releases software
=========================

``unleash`` is a medium-sized commandline utility that tries to ease releasing
software, specifically Python libraries and programs. It is currently barely
documented and tailored to my workflow. Use at your own risk.

Examples
--------

Creating a new release
**********************

Simply do::

    unleash create-release

This will:

  * Read the version currently in master and calculate the appropriate release
    version (i.e. 0.3.4.dev1 becomes 0.3.4).
  * Create a new commit, in which ``setup.py`` and ``packagename/__init__.py``
    have had their version strings updated to the new version.
  * Check out the commit in a temporary directory, alongside a clean
    `virtualenv <http://virtualenv.org>`_.
  * Check if the documentation, if present, can be built correctly.
  * Generate an ``sdist`` package from the checked out commit and see if it
    cleanly installs inside the virtualenv.
  * Runs unittests inside the virtualenv.
  * If everything goes well, removes the temporary checkouts/virtualenvs and
    tags the commit with the new version.
  * Creates a new commit on master with a version bump for the next release.

Git operations are not done on the working copy, but directly using dulwich,
avoiding snafu's that plague other forms of scripting releases. The only
actual call to the git-executable is when pushing a tag.


Publish a release
*****************

Creating a release can be followed up with something like::

    unleash publish -s code

This will:

  * Check out the latest version tag into a temporary directory.
  * Build a source package.
  * Upload and sign it (``python setup.py sdist -s -i code``).
  * Upload the documentation, if present, to pythonhosted.org (PyPI).
  * Push the associated git tag to origin.
  * Clean up the temporary directory.
