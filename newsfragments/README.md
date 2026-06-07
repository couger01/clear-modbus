# News Fragments

Towncrier uses this directory to collect release-note fragments before each
release.

Create a fragment with:

```bash
uv run towncrier create ISSUE.TYPE.md
```

Use `+` instead of an issue number for changes that do not have a GitHub issue:

```bash
uv run towncrier create +.doc.md
```

Supported fragment types:

- `feature` for new user-facing behavior
- `bugfix` for fixed behavior
- `doc` for documentation-only changes
- `removal` for removed behavior
- `misc` for maintenance changes that users may still care about

Before a release, build the changelog with:

```bash
uv run towncrier build --version 0.1.0
```
