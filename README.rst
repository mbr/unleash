Unleash your code
=================

``unleash`` handles the boring details of cutting a release and publishing it
to somewhere. It assists you doing things like updating version numbers, make
sure the documentation builds, reminding you that you still need to include a
LICENSE file and other things.

Once a release is made, it gets tagged in your git repository and you can use
the publish-functionality to push the new tag to github.com and/or upload your
package to `PyPI <http://pypi.python.org>`_

Unleash always works with commits, not files in your working copy and creates
temporary checkouts or verifies directly from the commit's tree. This way you
can be sure it's not working on your machine only, because you forgot to
check-in that crucial file that's missing from the release commit.


Examples
--------

.. code-block:: shell

   $ unleash --dry-run release
   Updating setup.py and package version (0.6.0)
   Updating documentation version (now 0.6.0)
   Marking release as released by unleash
   Checking documentation builds cleanly
   Verifying release can generate source distribution
   Verifying release can install into a virtualenv
   Running tox tests
   Updating setup.py and package version (0.6.1.dev1)
   Updating documentation version (now 0.6.1.dev1)
   Not saving created commits. Dry-run successful.

Note the ``--dry-run`` option which means that no alterations will be made to
your repository. Otherwise, unleash will prompt you to confirm to create a new
tag ``0.6.0`` for the release and will offer to advance your current branch to
the next commit, in which all version numbers have been increase.

.. code-block:: shell

   $ unleash --dry-run publish

To be written.


Other features
--------------

``unleash`` uses a plugin-based architecture for all of its operations, this
means it is fairly easy to add custom checks and steps for releases or
publications if you desire so.

See the documentation at http://pythonhosted.org/unleash for details.
