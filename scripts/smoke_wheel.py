"""Smoke test an already built clear-modbus wheel in a clean virtualenv."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
IMPORT_CHECK = """
from clear_modbus import (
    ModbusRtuClient,
    ModbusSimulator,
    ModbusTcpClient,
    ReadHoldingRegistersRequest,
)

assert ModbusTcpClient is not None
assert ModbusRtuClient is not None
assert ModbusSimulator is not None
assert ReadHoldingRegistersRequest(address=0, count=1).encode() == b"\\x03\\x00\\x00\\x00\\x01"
"""


def main() -> int:
    """Install the newest built wheel into a temporary venv and import it."""
    wheels = sorted(DIST.glob("clear_modbus-*.whl"), key=lambda path: path.stat().st_mtime)
    if not wheels:
        print("No built wheel found. Run `uv build` first.", file=sys.stderr)
        return 1

    wheel = wheels[-1]
    with tempfile.TemporaryDirectory(prefix="clear-modbus-wheel-") as temp_dir:
        venv_dir = Path(temp_dir) / ".venv"
        venv.EnvBuilder(with_pip=True).create(venv_dir)

        python = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
            check=True,
        )
        subprocess.run([str(python), "-c", IMPORT_CHECK], check=True)

    print(f"Smoke tested {wheel.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
