Releasing
=========

Releases are cut from ``main``. Keep ``main`` releasable, prepare release
metadata in a short release PR, and tag the merge commit after CI passes.

Use release branches only for maintenance fixes to an older release line after
``main`` has moved on to the next minor or major version.

Release PR
----------

1. Choose the final version, for example ``0.2.0``.
2. Update ``pyproject.toml`` from the current development version to the final
   release version.
3. Build release notes from the pending Towncrier fragments:

   .. code-block:: bash

      uv run towncrier build --version 0.2.0

4. Review ``CHANGELOG.md`` and confirm the consumed fragments were removed.
5. Run the normal checks:

   .. code-block:: bash

      uv run nox

6. Merge the release PR after CI passes.

Tagging
-------

Tag the release PR merge commit with a ``v``-prefixed tag and push it:

.. code-block:: bash

   git switch main
   git pull --ff-only
   git tag v0.2.0
   git push origin v0.2.0

Automation
----------

The package and release automation is split across two workflows:

``Build Package``
   Runs on ``v*`` tags, builds the source distribution and wheel with
   ``uv build``, smoke tests the wheel, and uploads the ``dist`` files as a
   workflow artifact.

``Release``
   Runs after a successful ``Build Package`` workflow, downloads the package
   artifact from that workflow run, extracts the matching ``CHANGELOG.md``
   section, and creates a GitHub Release with the source distribution and wheel
   attached.

The release notes come from the Towncrier-generated changelog section matching
the tag version. For example, ``v0.2.0`` uses the ``0.2.0`` section.

After a Release
---------------

Open a follow-up PR that bumps ``pyproject.toml`` to the next development
version, for example ``0.2.1.dev1`` or ``0.3.0.dev1``.
