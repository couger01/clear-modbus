"""Nox sessions for clear-modbus."""

from __future__ import annotations

from nox import Session, options
from nox_uv import session

PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]

options.default_venv_backend = "uv"
options.reuse_existing_virtualenvs = True
options.sessions = ["tests", "docs", "pre_commit"]


@session(python=PYTHON_VERSIONS, uv_groups=["test"])
def tests(session: Session) -> None:
    """Run the test suite."""
    session.run("pytest", *session.posargs)


@session(python=PYTHON_VERSIONS[-1], uv_groups=["bench"])
def benchmarks(session: Session) -> None:
    """Run microbenchmarks."""
    session.run("python", "benchmarks/protocol.py", *session.posargs)
    session.run("python", "benchmarks/datastore.py", *session.posargs)
    session.run("python", "benchmarks/server.py", *session.posargs)


@session(python=PYTHON_VERSIONS[-1], uv_groups=["docs"])
def docs(session: Session) -> None:
    """Build the Sphinx documentation."""
    session.run(
        "sphinx-build",
        "-W",
        "--keep-going",
        "-b",
        "html",
        "doc",
        "doc/_build/html",
        *session.posargs,
    )


@session(python=PYTHON_VERSIONS[-1], uv_groups=["pre-commit"])
def pre_commit(session: Session) -> None:
    """Run pre-commit hooks against all files."""
    session.run("pre-commit", "run", "-a", *session.posargs)
