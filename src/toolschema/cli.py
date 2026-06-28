from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from toolschema import schema
from toolschema._ir import ToolDefinition

_FORMATTERS = {
    "canonical": lambda t: t.to_json_schema(),
    "openai": lambda t: t.to_openai(),
    "openai-strict": lambda t: t.to_openai(strict=True),
    "anthropic": lambda t: t.to_anthropic(),
    "mcp": lambda t: t.to_mcp(),
    "gemini": lambda t: t.to_gemini(),
}


def _resolve_target(target: str) -> Callable[..., Any]:
    if ":" not in target:
        raise argparse.ArgumentTypeError(
            f"Target must be MODULE:FUNCTION or MODULE:OBJECT.attr, got {target!r}"
        )
    module_path, qualname = target.split(":", 1)
    module = importlib.import_module(module_path)
    obj: Any = module
    for part in qualname.split("."):
        obj = getattr(obj, part)
    if not callable(obj):
        raise argparse.ArgumentTypeError(f"{target!r} is not callable")
    return obj


def _parse_formats(value: str) -> list[str]:
    formats = [part.strip() for part in value.split(",") if part.strip()]
    unknown = set(formats) - set(_FORMATTERS)
    if unknown:
        raise argparse.ArgumentTypeError(f"Unknown format(s): {', '.join(sorted(unknown))}")
    return formats


def _emit(data: Any) -> None:
    print(json.dumps(data, indent=2))


def cmd_inspect(args: argparse.Namespace) -> int:
    fn = _resolve_target(args.target)
    tool = schema(fn)
    formats = _parse_formats(args.format)
    if len(formats) == 1:
        _emit(_FORMATTERS[formats[0]](tool))
        return 0

    result = {fmt: _FORMATTERS[fmt](tool) for fmt in formats}
    _emit(result)
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    fn = _resolve_target(args.target)
    tool = schema(fn)
    targets = _parse_formats(args.targets)
    payloads = {fmt: _FORMATTERS[fmt](tool) for fmt in targets}
    if len(payloads) < 2:
        _emit({"message": "Nothing to diff; provide at least two targets", "payloads": payloads})
        return 0

    names = list(payloads)
    diffs: dict[str, Any] = {}
    for left, right in zip(names, names[1:], strict=False):
        diffs[f"{left}_vs_{right}"] = {
            "equal": payloads[left] == payloads[right],
            "left_keys": sorted(_collect_keys(payloads[left])),
            "right_keys": sorted(_collect_keys(payloads[right])),
        }
    _emit({"target": args.target, "diffs": diffs, "payloads": payloads})
    return 0


def _collect_keys(obj: Any, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            keys.add(path)
            keys.update(_collect_keys(value, path))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            path = f"{prefix}[{index}]"
            keys.update(_collect_keys(value, path))
    return keys


def _discover_tools(module_path: str) -> list[tuple[str, Callable[..., Any]]]:
    module = importlib.import_module(module_path)
    tools: list[tuple[str, Callable[..., Any]]] = []
    for name in sorted(dir(module)):
        if name.startswith("_"):
            continue
        obj = getattr(module, name)
        if callable(obj):
            tools.append((name, obj))
    return tools


def cmd_export(args: argparse.Namespace) -> int:
    tools: list[dict[str, Any]] = []
    for name, fn in _discover_tools(args.module):
        try:
            tool: ToolDefinition = schema(fn)
        except (TypeError, ValueError):
            continue
        tools.append(tool.to_json_schema() | {"_source": f"{args.module}:{name}"})

    payload = {"module": args.module, "tools": tools}
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    else:
        _emit(payload)
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    from toolschema._init_scaffold import scaffold_mcp_server

    result = scaffold_mcp_server(Path(args.path), args.name)
    print(f"Created MCP server at {result.root}")
    print("Next steps:")
    print(f"  cd {result.project_name}")
    print("  uv sync")
    print(f"  uv run python -m {result.package_name} --check")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toolschema", description="Inspect Python tool schemas")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect", help="Inspect a function as provider tool JSON")
    inspect_parser.add_argument("target", help="MODULE:FUNCTION")
    inspect_parser.add_argument(
        "--format",
        default="canonical",
        help="Output format: canonical,openai,openai-strict,anthropic,mcp,gemini",
    )
    inspect_parser.set_defaults(func=cmd_inspect)

    diff_parser = sub.add_parser("diff", help="Compare provider outputs for a function")
    diff_parser.add_argument("target", help="MODULE:FUNCTION")
    diff_parser.add_argument(
        "--targets",
        default="openai,mcp",
        help="Comma-separated formats to compare",
    )
    diff_parser.set_defaults(func=cmd_diff)

    export_parser = sub.add_parser("export", help="Export schemas for callable objects in a module")
    export_parser.add_argument("module", help="Python module path")
    export_parser.add_argument("--output", help="Write JSON to file instead of stdout")
    export_parser.set_defaults(func=cmd_export)

    init_parser = sub.add_parser("init", help="Scaffold a new MCP server project")
    init_parser.add_argument("name", help="Project directory name")
    init_parser.add_argument(
        "--path",
        default=".",
        help="Parent directory where the project folder is created (default: current directory)",
    )
    init_parser.set_defaults(func=cmd_init)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except argparse.ArgumentTypeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
