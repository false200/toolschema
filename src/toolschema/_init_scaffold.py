from __future__ import annotations

import re
import shutil
from importlib import resources
from pathlib import Path
from typing import NamedTuple


class ScaffoldResult(NamedTuple):
    root: Path
    package_name: str
    project_name: str


def slugify_package_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug:
        raise ValueError("Project name must contain at least one letter or digit")
    if slug[0].isdigit():
        slug = f"mcp_{slug}"
    return slug


def _render(text: str, *, project_name: str, package_name: str, project_title: str) -> str:
    return (
        text.replace("{{project_name}}", project_name)
        .replace("{{package_name}}", package_name)
        .replace("{{project_title}}", project_title)
    )


def scaffold_mcp_server(target_dir: Path, project_name: str) -> ScaffoldResult:
    """Scaffold a new MCP server project from the packaged template."""
    package_name = slugify_package_name(project_name)
    project_title = project_name.replace("-", " ").replace("_", " ").title()
    root = target_dir.resolve() / project_name

    if root.exists():
        raise FileExistsError(f"Directory already exists: {root}")

    template_root = resources.files("toolschema.templates") / "mcp_server"
    _copy_template_tree(template_root, root)

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        rendered = _render(
            content,
            project_name=project_name,
            package_name=package_name,
            project_title=project_title,
        )
        path.write_text(rendered, encoding="utf-8")

    package_dir = root / "src" / "PACKAGE"
    final_package_dir = root / "src" / package_name
    package_dir.rename(final_package_dir)

    return ScaffoldResult(root=root, package_name=package_name, project_name=project_name)


def _copy_template_tree(source: resources.abc.Traversable, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.is_dir():
            _copy_template_tree(item, destination / item.name)
        else:
            shutil.copyfile(item, destination / item.name)
