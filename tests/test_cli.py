from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_TESTS_DIR = Path(__file__).parent
_PYTHONPATH = os.pathsep.join([str(_TESTS_DIR), os.environ.get("PYTHONPATH", "")])
_ENV = {**os.environ, "PYTHONPATH": _PYTHONPATH}


def test_inspect_cli_mcp() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "toolschema", "inspect", "fixtures:sample_tool", "--format", "mcp"],
        capture_output=True,
        text=True,
        check=False,
        env=_ENV,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["name"] == "add"
    assert "inputSchema" in payload


def test_inspect_cli_multiple_formats() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "toolschema",
            "inspect",
            "fixtures:add",
            "--format",
            "openai,mcp",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=_ENV,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "openai" in payload
    assert "mcp" in payload


def test_diff_cli() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "toolschema",
            "diff",
            "fixtures:add",
            "--targets",
            "openai,mcp",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=_ENV,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "diffs" in payload


def test_export_skips_unresolved_annotation(tmp_path: Path) -> None:
    module = tmp_path / "export_mod.py"
    module.write_text(
        "def ok(a: int) -> int:\n"
        '    """Add."""\n'
        "    return a\n"
        "\n"
        "def broken(name: Missing) -> str:\n"
        '    """Broken."""\n'
        "    return name\n",
        encoding="utf-8",
    )
    env = {**_ENV, "PYTHONPATH": os.pathsep.join([str(tmp_path), _ENV["PYTHONPATH"]])}
    result = subprocess.run(
        [sys.executable, "-m", "toolschema", "export", "export_mod"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    names = [tool["name"] for tool in payload["tools"]]
    assert names == ["ok"]


def test_export_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "toolschema", "export", "fixtures"],
        capture_output=True,
        text=True,
        check=False,
        env=_ENV,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["module"] == "fixtures"
    assert any(tool["name"] == "add" for tool in payload["tools"])
