from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from toolschema._init_scaffold import scaffold_mcp_server, slugify_package_name


def test_slugify_package_name() -> None:
    assert slugify_package_name("My-MCP-Server") == "my_mcp_server"
    assert slugify_package_name("123demo") == "mcp_123demo"


def test_scaffold_mcp_server_creates_files(tmp_path: Path) -> None:
    result = scaffold_mcp_server(tmp_path, "demo-server")
    root = result.root

    assert root.is_dir()
    assert (root / "pyproject.toml").exists()
    assert (root / "README.md").exists()
    assert (root / "claude_desktop_config.example.json").exists()
    assert (root / "src" / "demo_server" / "tools.py").exists()
    assert (root / "src" / "demo_server" / "__main__.py").exists()

    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "demo-server" in readme
    assert "demo_server" in readme
    assert "{{" not in readme

    config = json.loads((root / "claude_desktop_config.example.json").read_text(encoding="utf-8"))
    assert "demo-server" in config["mcpServers"]


def test_init_cli(tmp_path: Path) -> None:
    target_parent = tmp_path / "parent"
    target_parent.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "toolschema",
            "init",
            "cli-demo",
            "--path",
            str(target_parent),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (target_parent / "cli-demo" / "src" / "cli_demo" / "tools.py").exists()


def test_scaffold_refuses_existing_directory(tmp_path: Path) -> None:
    (tmp_path / "exists").mkdir()
    try:
        scaffold_mcp_server(tmp_path, "exists")
        raised = False
    except FileExistsError:
        raised = True
    assert raised
