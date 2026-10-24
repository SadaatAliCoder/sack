"""
SACK CLI: compact structural context for AI-assisted codebases.
Copyright (C) 2026 Sadaqat Ali.
Licensed under the GNU General Public License v3.0 (GPL-3.0).
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

__version__ = "0.5.0"

IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "node_modules", "venv", ".venv", "env",
    "dist", "build", "target", "coverage", ".next", ".nuxt", ".svelte-kit",
    ".dart_tool", ".fvm", ".symlinks", "bin", "obj", ".vs", ".gradle",
    ".build", ".swiftpm", "pods", ".bundle", "vendor", ".tox", ".nox",
    ".cache", "out", ".cxx", ".turbo", ".output", "deriveddata",
}
EXTENSIONS = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts",
    ".rs", ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".go", ".java", ".php", ".dart", ".cs", ".kt", ".kts", ".swift", ".rb",
    ".html", ".css", ".scss", ".svelte", ".vue",
}
MARKUP_EXTENSIONS = {".html", ".css", ".scss"}
MAX_BYTES = 2_000_000
CACHE_NAME = ".sack_cache.json"
CONTEXT_NAME = "sack_context.txt"
GUARDRAILS_NAME = "sack_guardrails.md"
GENERATED_FILE_SUFFIXES = (
    ".min.js", ".min.css", ".bundle.js",
    ".g.dart", ".freezed.dart", ".mocks.dart",
    ".designer.cs", ".generated.cs", ".g.cs", ".g.i.cs",
    ".pb.go", ".gen.go", "_gen.go",
    "_pb2.py", "_pb2_grpc.py",
    ".moc.cpp",
)


def is_generated_or_minified(name: str) -> bool:
    """Check if a file is machine-generated or minified code that should be excluded."""
    name_lower = name.lower()
    return name_lower.endswith(GENERATED_FILE_SUFFIXES) or name_lower.startswith("moc_")


class ScanResult(tuple):
    """Result tuple for scan_project, preserving 3-element unpack while exposing stats."""
    def __new__(cls, scanned: int, warnings: list[str], changed: bool, stats: dict[str, Any] | None = None):
        instance = super().__new__(cls, (scanned, warnings, changed))
        instance.stats = stats or {}
        return instance

GUARDRAILS = """# SACK AI Code Generation Guardrails

## Universal rules
- Read `sack_context.txt` and the relevant source files before editing.
- Preserve architecture and public APIs unless explicitly asked to change them.
- Do not invent dependencies, configuration keys, or runtime behavior.
- Handle errors explicitly, add tests for new behavior, and avoid unrelated edits.
- Never hard-code secrets. State uncertainty rather than claiming unverified correctness.
- Run available tests, formatters, and type checkers when possible.

## Python
- Annotate every new or modified function/method parameter and return type.
- Add a concise PEP 257 docstring to every public function, method, and class.
- Prefer specific types such as `list[str]`, `dict[str, int]`, and `Path`.

## JavaScript
- Add JSDoc directly above exported functions/classes; include `@param` and `@returns`.
- Prefer `const`, validate external input, and handle rejected promises.

## TypeScript
- Explicitly type exported function parameters and return values.
- Use interfaces/type aliases for structured data; avoid unjustified `any`.
- Add JSDoc above exported functions, classes, interfaces, and types.

## Svelte
- In Svelte 4, declare props with explicit type annotations: `export let propName: Type = defaultValue;`.
- In Svelte 5, declare props with typed runes: `let { prop1, prop2 = default }: Props = $props();`, and manage state using `$state()` and `$derived()`.
- Do not mutate props directly; dispatch events (Svelte 4 `createEventDispatcher`) or invoke callback props (Svelte 5).
- Always clean up event listeners, timers, and subscriptions in `onDestroy` (Svelte 4) or `$effect` teardown (Svelte 5).

## Tauri
- Strictly type IPC calls: use `invoke<ReturnType>('command_name', { payload })` on the frontend and `#[tauri::command]` on the Rust backend.
- Keep argument names matching identically between Rust function parameters and frontend JSON payload keys.
- Always handle IPC errors gracefully using `try/catch` on the frontend and `Result<T, E>` in Rust commands.

## Flutter & Dart
- Use `const` constructors wherever possible to prevent unnecessary widget rebuilds.
- Strictly adhere to sound null safety; avoid unjustified `!` force unwraps and prefer `?` or default values.
- Check `if (!context.mounted) return;` after any `await` before using `BuildContext` across async gaps.
- Declare widget parameters as `final` fields and dispose controllers/streams in `dispose()`.

## Rust
- Give public functions explicit parameter and return types.
- Add `///` docs to every public function, struct, enum, trait, and public module.
- Prefer `Result<T, E>` for recoverable errors; avoid unnecessary `unwrap()`.

## C++
- Use explicit parameter and return types and document public APIs with `///` or `/** ... */`.
- Prefer const correctness, RAII, standard-library types, and consistent declarations/definitions.

## Go
- Use explicit parameter and return types.
- Add a Go doc comment above every exported identifier, beginning with its name.
- Handle errors rather than ignoring them.

## Java
- Use explicit parameter and return types where applicable.
- Add Javadoc to every public class, interface, enum, constructor, and public method.
- Prefer generics over raw collection types.

## PHP
- Declare parameter and return types for functions and methods.
- Add PHPDoc to public classes and methods, including `@param`, `@return`, and relevant `@throws`.
- Validate external input and type properties where supported.

## C#
- Annotate public APIs and controller actions with appropriate attributes (`[HttpGet]`, `[Authorize]`, etc.).
- Use explicit parameter and return types; prefer async `Task<T>` for asynchronous methods and configure cancellation tokens.
- Follow standard PascalCase naming conventions for classes, methods, and public properties.

## Kotlin
- Declare variables with `val` (immutable) whenever possible instead of `var`.
- Use Kotlin null-safety idioms (`?`, `?:`, `let`) and avoid `!!`.
- Use `data class` for data holders and `sealed class`/`sealed interface` for restricted class hierarchies.

## Swift
- Prefer `let` over `var` for immutability; leverage optionals and optional binding (`if let`, `guard let`).
- Use protocols and extensions to organize code and avoid massive view controllers/structs.
- Mark mutating methods explicitly in structs and actors.

## Ruby
- Follow the Ruby community style guide (snake_case for methods/variables, CamelCase for classes/modules).
- Prefer explicit return over ambiguous implicit values for complex public methods.
- Avoid modifying core or standard library classes (monkey patching).

## Completion checklist
1. Public functions have appropriate types and documentation.
2. Imports and module-level constants are consistent.
3. Tests cover the change and no unrelated files were modified.
4. Limitations and unverified behavior are disclosed.
"""


def unique(items: list[str]) -> list[str]:
    """Deduplicate non-empty strings while preserving order."""
    return list(dict.fromkeys(item.rstrip() for item in items if item.strip()))


def _python_extract(path: Path, source: str) -> dict[str, Any]:
    """Extract Python imports, globals, decorators, signatures, and docstrings."""
    result: dict[str, Any] = {"imports": [], "globals": [], "signatures": [], "warnings": []}
    try:
        tree = ast.parse(source, filename=str(path), type_comments=True)
    except SyntaxError as exc:
        result["warnings"].append(f"Python syntax error at line {exc.lineno}: {exc.msg}")
        return result

    def seg(node: ast.AST) -> str:
        """Return source text for an AST node."""
        return (ast.get_source_segment(source, node) or "").strip()

    def decorators(node: ast.AST) -> list[str]:
        """Format decorators attached to a Python declaration."""
        return [f"@{seg(item)}" for item in getattr(node, "decorator_list", [])]

    def function(node: ast.FunctionDef | ast.AsyncFunctionDef, indent: str = "") -> str:
        """Render a function signature, decorators, and concise docstring."""
        args = node.args
        positional = list(args.posonlyargs) + list(args.args)
        defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
        params: list[str] = []
        for index, (arg, default) in enumerate(zip(positional, defaults)):
            value = arg.arg
            if arg.annotation:
                value += f": {seg(arg.annotation)}"
            if default is not None:
                value += f" = {seg(default)}"
            if args.posonlyargs and index == len(args.posonlyargs) - 1:
                value += "/"
            params.append(value)
        if args.vararg:
            value = "*" + args.vararg.arg
            if args.vararg.annotation:
                value += f": {seg(args.vararg.annotation)}"
            params.append(value)
        elif args.kwonlyargs:
            params.append("*")
        for arg, default in zip(args.kwonlyargs, args.kw_defaults):
            value = arg.arg + (f": {seg(arg.annotation)}" if arg.annotation else "")
            if default is not None:
                value += f" = {seg(default)}"
            params.append(value)
        if args.kwarg:
            value = "**" + args.kwarg.arg
            if args.kwarg.annotation:
                value += f": {seg(args.kwarg.annotation)}"
            params.append(value)
        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        ret = f" -> {seg(node.returns)}" if node.returns else ""
        head = f"{indent}{prefix}def {node.name}({', '.join(params)}){ret}:"
        body = [indent + line for line in decorators(node)]
        body.append(head)
        doc = ast.get_docstring(node, clean=True)
        if doc:
            body.append(f'{indent}    """{doc.splitlines()[0].strip()}"""')
        return "\n".join(body)

    def klass(node: ast.ClassDef, indent: str = "") -> str:
        """Render a class, its decorators/docstring, and method signatures."""
        bases = [seg(base) for base in node.bases]
        bases.extend(seg(keyword) for keyword in node.keywords)
        text = [indent + line for line in decorators(node)]
        text.append(f"{indent}class {node.name}{'(' + ', '.join(bases) + ')' if bases else ''}:")
        doc = ast.get_docstring(node, clean=True)
        if doc:
            text.append(f'{indent}    """{doc.splitlines()[0].strip()}"""')
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                text.extend(["", function(child, indent + "    ")])
            elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                text.append(f"{indent}    {seg(child)}")
        return "\n".join(text)

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            result["imports"].append(seg(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["signatures"].append(function(node))
        elif isinstance(node, ast.ClassDef):
            result["signatures"].append(klass(node))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = seg(node)
            if value:
                result["globals"].append(value)
    for key in ("imports", "globals", "signatures"):
        result[key] = unique(result[key])
    return result


def _balanced_declaration(lines: list[str], start: int) -> tuple[str, int]:
    """Collect a multiline declaration until delimiters balance or a body starts."""
    collected = [lines[start].strip()]
    text = collected[0]
    # Declarations often span lines while parentheses/brackets/generics are open.
    # This is deliberately conservative and not a complete language parser.
    depth = text.count("(") + text.count("[") + text.count("{") - text.count(")") - text.count("]") - text.count("}")
    cursor = start + 1
    while cursor < len(lines) and cursor < start + 30:
        if depth <= 0 and not text.rstrip().endswith((",", "=", "->", ":", "extends", "implements")):
            break
        next_line = lines[cursor].strip()
        if not next_line or next_line.startswith(("//", "/*", "*", "#")):
            if depth > 0:
                cursor += 1
                continue
            break
        collected.append(next_line)
        text += " " + next_line
        depth += next_line.count("(") + next_line.count("[") + next_line.count("{") - next_line.count(")") - next_line.count("]") - next_line.count("}")
        cursor += 1
    return " ".join(collected), max(1, cursor - start)


def _extract_tauri_calls(source: str) -> list[str]:
    """Extract invoke, listen, and emit IPC calls from Tauri frontend code."""
    calls: list[str] = []
    # Match invoke calls with balanced parentheses for argument payloads
    for match in re.finditer(r"\binvoke\s*(?:<(?P<ret>[^>]+)>)?\s*\(\s*(?P<cmd>['\"][^'\"]+['\"])", source):
        ret = match.group("ret")
        cmd = match.group("cmd").strip()
        start_idx = match.end()
        depth = 1
        cursor = start_idx
        while cursor < len(source) and depth > 0:
            ch = source[cursor]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            cursor += 1
        raw_args = source[start_idx:cursor - 1].strip()
        arg_str = ""
        if raw_args.startswith(","):
            arg_str = re.sub(r"\s+", " ", raw_args[1:].strip())
            if len(arg_str) > 60:
                arg_str = arg_str[:57] + "..."
        type_str = f"<{ret.strip()}>" if ret else ""
        if arg_str:
            calls.append(f"invoke{type_str}({cmd}, {arg_str})")
        else:
            calls.append(f"invoke{type_str}({cmd})")

    # Match listen calls
    for match in re.finditer(r"\blisten\s*(?:<(?P<ret>[^>]+)>)?\s*\(\s*(?P<event>['\"][^'\"]+['\"])", source):
        event = match.group("event").strip()
        ret = match.group("ret")
        type_str = f"<{ret.strip()}>" if ret else ""
        calls.append(f"listen{type_str}({event})")

    # Match emit calls
    for match in re.finditer(r"\bemit\s*\(\s*(?P<event>['\"][^'\"]+['\"])", source):
        event = match.group("event").strip()
        calls.append(f"emit({event})")

    return unique(calls)


def _svelte_extract(path: Path, source: str) -> dict[str, Any]:
    """Extract Svelte component props (v4 and v5 runes), state, types, Tauri calls, and signatures."""
    result: dict[str, Any] = {"imports": [], "globals": [], "signatures": [], "warnings": []}
    lines = source.splitlines()

    # Find all <script> blocks (instance and module scripts)
    script_blocks = list(re.finditer(r"<script\b([^>]*)>(.*?)</script\s*>", source, re.I | re.DOTALL))
    if not script_blocks:
        result["signatures"] = [f"[Svelte] {path.as_posix()} ({len(lines)} lines - template only)"]
        return result

    # 1. Extract Tauri calls anywhere in component
    tauri_calls = _extract_tauri_calls(source)
    if tauri_calls:
        result["globals"].extend(f"[Tauri] {c}" for c in tauri_calls)

    # 2. Extract emitted events (createEventDispatcher and dispatch calls)
    for disp_match in re.finditer(r"createEventDispatcher\s*<\s*\{([^}]+)\}\s*>", source, re.DOTALL):
        for entry in disp_match.group(1).split(";"):
            ev = entry.split(":")[0].strip()
            if ev:
                result["globals"].append(f"[Event Emitted] '{ev}'")
    for m in re.finditer(r"\bdispatch\s*\(\s*(['\"][^'\"]+['\"])", source):
        result["globals"].append(f"[Event Emitted] {m.group(1).strip()}")

    # 3. Process script blocks
    for match in script_blocks:
        attrs = match.group(1)
        code = match.group(2)
        is_module = bool(re.search(r"\b(?:context\s*=\s*['\"]module['\"]|module)\b", attrs, re.I))
        script_lines = code.splitlines()

        cursor = 0
        while cursor < len(script_lines):
            line = script_lines[cursor].strip()
            if not line:
                cursor += 1
                continue

            # Imports
            if re.match(r"^(?:import\b|export\s+.*\sfrom\b)", line):
                decl, consumed = _balanced_declaration(script_lines, cursor)
                result["imports"].append(decl)
                cursor += consumed
                continue

            # Svelte 5 $props Rune
            if "$props" in line and re.match(r"^(?:let|const)\s+", line):
                decl, consumed = _balanced_declaration(script_lines, cursor)
                result["globals"].append(f"[Rune $props] {decl.rstrip(';')}")
                cursor += consumed
                continue

            # Svelte 5 $state or $derived Runes
            if any(rune in line for rune in ("$state", "$derived")) and re.match(r"^(?:let|const)\s+", line):
                decl, consumed = _balanced_declaration(script_lines, cursor)
                result["globals"].append(f"[Rune] {decl.rstrip(';')}")
                cursor += consumed
                continue

            # Svelte 4 Props: export let ...
            m_prop = re.match(r"^export\s+let\s+([^;]+)", line)
            if m_prop:
                decl, consumed = _balanced_declaration(script_lines, cursor)
                result["globals"].append(f"[Prop] {decl.rstrip(';')}")
                cursor += consumed
                continue

            # Svelte 4 Reactive statement: $: varName = ...
            m_rx = re.match(r"^(\$:\s*[\w$]+\s*=\s*[^;]+)", line)
            if m_rx:
                decl, consumed = _balanced_declaration(script_lines, cursor)
                result["globals"].append(f"[Reactive] {decl.rstrip(';')}")
                cursor += consumed
                continue

            # Module exports (constants / variables in <script module>)
            if is_module and re.match(r"^export\s+(?:const|let|var)\s+[\w$]+", line):
                decl, consumed = _balanced_declaration(script_lines, cursor)
                result["globals"].append(f"[Module Export] {decl.rstrip(';')}")
                cursor += consumed
                continue

            # TypeScript interfaces & types
            if re.match(r"^(?:export\s+)?(?:interface|type|enum)\s+\w+", line):
                decl, consumed = _balanced_declaration(script_lines, cursor)
                result["signatures"].append(decl)
                cursor += consumed
                continue

            # Functions: function / async function / export function
            if re.match(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+[\w$]+\s*\(", line):
                decl, consumed = _balanced_declaration(script_lines, cursor)
                header = decl.split("{")[0].strip() if "{" in decl else decl
                result["signatures"].append(header)
                cursor += consumed
                continue

            # Arrow functions: const fn = () => or export const fn = () =>
            m_arrow = re.match(r"^((?:export\s+)?const\s+[\w$]+\s*=\s*(?:async\s*)?\([^)]*\)(?:\s*:\s*.+?)?\s*=>)", line)
            if m_arrow:
                result["signatures"].append(m_arrow.group(1))
                cursor += 1
                continue

            # General top-level constants / variables / stores
            if re.match(r"^(?:const|let|var)\s+[\w$]+(?:\s*:\s*[^=;]+)?\s*=", line):
                decl, consumed = _balanced_declaration(script_lines, cursor)
                if "$props" not in decl and "$state" not in decl and "$derived" not in decl:
                    result["globals"].append(decl.rstrip(";"))
                cursor += consumed
                continue

            cursor += 1

    for key in ("imports", "globals", "signatures"):
        result[key] = unique(result[key])
    return result


def _other_extract(path: Path, source: str) -> dict[str, Any]:
    """Extract approximate dependencies, globals, and declarations from other languages."""
    ext = path.suffix.lower()
    result: dict[str, Any] = {"imports": [], "globals": [], "signatures": [], "warnings": []}
    lines = source.splitlines()

    if ext in MARKUP_EXTENSIONS:
        result["signatures"] = [f"[Markup] {path.as_posix()} ({len(lines)} lines - AST Skipped)"]
        return result
    if ext == ".vue":
        blocks = re.findall(r"<script\b([^>]*)>(.*?)</script\s*>", source, re.I | re.S)
        if not blocks:
            result["signatures"] = [f"[Markup] {path.as_posix()} ({len(lines)} lines - no script block)"]
            return result
        is_ts = any("ts" in b[0].lower() for b in blocks)
        lines = "\n".join(b[1] for b in blocks).splitlines()
        lang = "ts" if is_ts else "js"
        # Check for Tauri calls in Vue files
        tauri_calls = _extract_tauri_calls(source)
        if tauri_calls:
            result["globals"].extend(f"[Tauri] {c}" for c in tauri_calls)
    else:
        ext_groups = {
            "js": {".js", ".jsx", ".mjs", ".cjs"},
            "ts": {".ts", ".tsx", ".mts", ".cts"},
            "rust": {".rs"},
            "cpp": {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"},
            "go": {".go"}, "java": {".java"}, "php": {".php"},
            "dart": {".dart"},
            "csharp": {".cs"},
            "kotlin": {".kt", ".kts"},
            "swift": {".swift"},
            "ruby": {".rb"},
        }
        lang = next((key for key, vals in ext_groups.items() if ext in vals), "js")

    imports = {
        "js": r"^(?:import\b|export\s+.*\sfrom\b|const\s+\w+\s*=\s*require\s*\()",
        "ts": r"^(?:import\b|export\s+.*\sfrom\b|const\s+\w+\s*=\s*require\s*\()",
        "rust": r"^(?:use\b|mod\s+\w+\s*;)",
        "cpp": r"^#include\b",
        "go": r"^(?:package\s+\w+|import\b)",
        "java": r"^(?:package\b|import\b)",
        "php": r"^(?:namespace\b|use\b|require(?:_once)?\b|include(?:_once)?\b)",
        "dart": r"^(?:import\b|export\b|part\b)",
        "csharp": r"^(?:(?:global\s+)?using\b|namespace\b)",
        "kotlin": r"^(?:package\b|import\b)",
        "swift": r"^(?:@testable\s+)?import\b",
        "ruby": r"^(?:require\b|require_relative\b|include\b|extend\b)",
    }
    globals_patterns = {
        "js": r"^(?:export\s+)?(?:const|let|var)\s+[\w$]+(?:\s*:\s*[^=;]+)?\s*=",
        "ts": r"^(?:export\s+)?(?:declare\s+)?(?:const|let|var)\s+[\w$]+(?:\s*:\s*[^=;]+)?\s*=",
        "rust": r"^(?:pub(?:\([^)]*\))?\s+)?(?:const|static)\s+\w+",
        "cpp": r"^(?:extern\s+)?(?:const\s+)?[\w:*&<>]+\s+\w+\s*(?:=|;)",
        "go": r"^(?:const|var)\s+\w+",
        "java": r"^(?:(?:public|private|protected|static|final)\s+)+[\w<>\[\].]+\s+\w+\s*(?:=|;)",
        "php": r"^(?:const\s+\w+|(?:public|protected|private)?\s*\$[A-Za-z_]\w*\s*=)",
        "dart": r"^(?!(?:class|typedef|enum|mixin|extension)\b)(?:(?:static\s+)?(?:late\s+)?(?:final\s+|const\s+|var\s+)?(?:[\w<>?,\[\]]+\s+)?[\w$]+\s*=)",
        "csharp": r"^(?:(?:public|private|protected|internal|static|readonly|const)\s+)+[\w<>?,\[\]\s*]+\s+\w+\s*(?:=|;)",
        "kotlin": r"^(?:(?:public|private|protected|internal)\s+)?(?:const\s+)?(?:lateinit\s+)?(?:val|var)\s+\w+",
        "swift": r"^(?:@\w+(?:\([^)]*\))?\s+)?(?:(?:public|private|fileprivate|internal|open|static)\s+)?(?:let|var)\s+\w+",
        "ruby": r"^(?:[A-Z]\w*|[$@]{1,2}\w+)\s*=",
    }
    declarations = {
        "js": r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+[\w$]+\s*\(|^(?:export\s+)?(?:default\s+)?class\s+\w+|^(?:export\s+)?(?:const|let|var)\s+[\w$]+\s*(?::[^=]+)?=",
        "ts": r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+[\w$]+\s*\(|^(?:export\s+)?(?:interface|type|enum|class)\s+\w+|^(?:export\s+)?(?:const|let|var)\s+[\w$]+\s*(?::[^=]+)?=",
        "rust": r"^(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+\w+|^(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait)\s+\w+",
        "cpp": r"^(?:template\s*<.*>|(?:[\w:*&<>\[\],]+\s+)+[*&]?\w+\s*\([^;]*\)\s*(?:const\s*)?(?:;|\{)?)|^(?:class|struct|enum)\s+\w+",
        "go": r"^func\s+(?:\([^)]*\)\s*)?\w+\s*\(|^type\s+\w+\s+(?:struct|interface)",
        "java": r"^(?:(?:public|protected|private|static|final|abstract|synchronized)\s+)*[\w<>?,.\[\]]+\s+\w+\s*\(|^(?:public\s+)?(?:class|interface|enum|record)\s+\w+",
        "php": r"^(?:(?:public|protected|private|static|final|abstract)\s+)*function\s+&?\s*\w+\s*\(|^(?:abstract\s+)?class\s+\w+|^(?:interface|trait|enum)\s+\w+",
        "dart": r"^(?:abstract\s+)?class\s+\w+|^(?:mixin|enum|extension)\s+\w+|^typedef\s+\w+|^(?:const\s+)?(?:factory\s+)?\w+(?:\.\w+)?\s*\([^;{]*\)|^(?!return\b|throw\b|yield\b|super\b|await\b)(?:[\w<>?,\[\]]+\s+)+(?:get\s+|set\s+)?[\w$]+\s*\(",
        "csharp": r"^(?:(?:public|private|protected|internal|static|abstract|virtual|override|async|sealed|partial)\s+)*(?:class|interface|struct|record|enum)\s+\w+|(?:(?:public|private|protected|internal|static|abstract|virtual|override|async|sealed)\s+)+[\w<>?,\[\]\s*]+\s+\w+\s*\([^;]*\)",
        "kotlin": r"^(?:(?:public|private|protected|internal|abstract|open|sealed|data|enum|annotation)\s+)*(?:class|interface|object)\s+\w+|^(?:(?:public|private|protected|internal|inline|suspend|override|open)\s+)*fun\s+(?:<[^>]+>\s+)?\w+\s*\(",
        "swift": r"^(?:(?:public|private|fileprivate|internal|open|final)\s+)*(?:struct|class|actor|protocol|enum|extension)\s+\w+|^(?:(?:public|private|fileprivate|internal|open|override|mutating|static)\s+)*(?:func\s+\w+|init\s*\(|deinit\b|var\s+body\b)",
        "ruby": r"^(?:class|module)\s+[A-Z]\w*|^def\s+(?:self\.)?[\w?!]+",
    }

    comments: list[str] = []
    skip_until = -1
    for index, raw in enumerate(lines):
        if index < skip_until:
            continue
        line = raw.strip()
        if not line:
            continue
        if (
            line.startswith(("///", "//!", "/**", "/*", "*"))
            or (lang == "ruby" and line.startswith("#"))
            or (lang == "rust" and line.startswith("#["))
            or (lang == "csharp" and line.startswith("[") and line.endswith("]") and not re.search(r"\b(?:var|return|throw|new)\b", line))
            or (
                lang in {"js", "ts", "java", "php", "dart", "kotlin", "swift"}
                and line.startswith("@")
                and not re.search(r"\b(?:var|let|val|fun|func|class|struct|interface|def)\b", line)
            )
        ):
            comments.append(line)
            continue
        if re.match(imports[lang], line):
            decl, consumed = _balanced_declaration(lines, index)
            result["imports"].append(decl)
            skip_until = index + consumed
            comments.clear()
            continue
        if re.match(globals_patterns[lang], line):
            decl, consumed = _balanced_declaration(lines, index)
            result["globals"].append(decl)
            skip_until = index + consumed
            comments.clear()
            continue
        if re.match(declarations[lang], line):
            declaration, consumed = _balanced_declaration(lines, index)
            decorators = []
            if comments:
                decorators.extend(comments)
            result["signatures"].append(("\n".join(decorators) + "\n" if decorators else "") + declaration)
            skip_until = index + consumed
        comments.clear()

    for key in ("imports", "globals", "signatures"):
        result[key] = unique(result[key])
    return result


def extract(path: Path, source: str) -> dict[str, Any]:
    """Dispatch extraction according to the source file extension."""
    suffix = path.suffix.lower()
    if suffix == ".py":
        return _python_extract(path, source)
    if suffix == ".svelte":
        return _svelte_extract(path, source)
    return _other_extract(path, source)


def _module_candidates(path_text: str) -> set[str]:
    """Create candidate import names from a relative project path."""
    path = Path(path_text)
    no_suffix = path.with_suffix("").as_posix()
    values = {
        no_suffix,
        no_suffix.replace("/", "."),
        path.stem,
        path.as_posix(),
        path.name,
        path.as_posix().replace("/", "."),
    }
    if path_text.startswith("lib/"):
        no_lib = path_text.removeprefix("lib/")
        p_nl = Path(no_lib)
        values.add(no_lib)
        values.add(p_nl.as_posix().replace("/", "."))
        values.add(p_nl.with_suffix("").as_posix())
        values.add(p_nl.with_suffix("").as_posix().replace("/", "."))
    if path.name.startswith("index."):
        values.add(path.parent.as_posix().replace("/", "."))
        values.add(path.parent.as_posix())
    if path.name == "__init__.py":
        values.add(path.parent.as_posix().replace("/", "."))
        values.add(path.parent.as_posix())
    return {v.removeprefix("./") for v in values if v and v != "."}


def build_dependency_graph(files: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Map files to project files that their imports appear to reference."""
    candidates: dict[str, set[str]] = {}
    for rel in files:
        for candidate in _module_candidates(rel):
            candidates.setdefault(candidate.lower(), set()).add(rel)
    graph: dict[str, list[str]] = {}
    for rel, facts in files.items():
        targets: set[str] = set()
        for imp in facts.get("imports", []):
            # Strip comments and quote delimiters to avoid matching arbitrary prose.
            clean = imp.strip()
            match = re.search(r"(?:from\s+|import\s+|export\s+|part\s+|using\s+(?:static\s+)?|use\s+|require\s*\(\s*|=\s*['\"])(['\"]?)([\w./@$:-]+)", clean)
            if match:
                raw_mod = match.group(2).strip(".'\";")
                # Handle path aliases like package:app_name/, crate::, $lib/, @/
                module = re.sub(r"^(?:package:[\w-]+/|crate::|[$@]\w*/)", "", raw_mod)
                normalized = module.replace("/", ".").replace("::", ".").lower()
                stem = Path(module).stem.lower()
                mod_name = Path(module).name.lower()
                for candidate, paths in candidates.items():
                    if (
                        candidate == normalized
                        or candidate.endswith("." + normalized)
                        or normalized.endswith("." + candidate)
                        or candidate == module.lower()
                        or candidate == mod_name
                        or (stem and candidate == stem)
                    ):
                        targets.update(p for p in paths if p != rel)
            # Rust paths and C includes can contain project-relative path fragments.
            for candidate, paths in candidates.items():
                if candidate and candidate in clean.lower():
                    targets.update(p for p in paths if p != rel)
        graph[rel] = sorted(targets)
    return graph


def _render_context(root: Path, facts: dict[str, dict[str, Any]], markup: dict[str, str]) -> str:
    """Render dependency graph first, then imports/globals, then signatures."""
    graph = build_dependency_graph(facts)
    output: list[str] = [
        "SACK CONTEXT INDEX",
        f"Project root: {root}",
        "",
        "=" * 54,
        "DEPENDENCY OVERVIEW",
        "=" * 54,
    ]
    if not graph:
        output.append("(no source modules found)")
    for rel in sorted(graph):
        deps = graph[rel]
        output.append(f"{rel} -> {', '.join(deps) if deps else '(no internal dependency detected)'}")

    output.extend(["", "=" * 54, "CORE IMPORTS & GLOBALS", "=" * 54])
    for rel in sorted(facts):
        item = facts[rel]
        output.extend(["", f"FILE: {rel}", "[IMPORTS]", *(item["imports"] or ["(none detected)"]),
                       "[GLOBALS]", *(item["globals"] or ["(none detected)"])])
    if markup:
        output.extend(["", "=" * 54, "MARKUP / ASSET SUMMARIES", "=" * 54])
        output.extend(markup[key] for key in sorted(markup))

    output.extend(["", "=" * 54, "FUNCTION & CLASS SIGNATURES", "=" * 54])
    for rel in sorted(facts):
        output.extend(["", f"FILE: {rel}", *(facts[rel]["signatures"] or ["(no supported declarations detected)"])])
    output.append("")
    return "\n".join(output)


def scan_project(root: Path, changed: bool = False) -> tuple[int, list[str], bool]:
    """Scan a project, optionally reusing cached extraction for unchanged files."""
    root = root.resolve()
    cache_path = root / CACHE_NAME
    output_path = root / CONTEXT_NAME
    old_cache: dict[str, Any] = {}
    if changed and cache_path.exists():
        try:
            old_cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            old_cache = {}
    old_files: dict[str, Any] = old_cache.get("files", {})
    current: dict[str, tuple[Path, int, int]] = {}
    for folder, dirs, names in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = sorted(
            d for d in dirs
            if d.lower() not in IGNORED_DIRS
            and not d.lower().endswith(".egg-info")
            and not (Path(folder) / d).is_symlink()
        )
        for name in sorted(names):
            if is_generated_or_minified(name):
                continue
            path = Path(folder) / name
            if path.suffix.lower() not in EXTENSIONS or name in {CONTEXT_NAME, GUARDRAILS_NAME, CACHE_NAME}:
                continue
            rel = path.relative_to(root).as_posix()
            try:
                stat = path.stat()
                if path.is_symlink() or stat.st_size > MAX_BYTES:
                    continue
                current[rel] = (path, stat.st_mtime_ns, stat.st_size)
            except OSError:
                continue

    files: dict[str, dict[str, Any]] = {}
    markup: dict[str, str] = {}
    warnings: list[str] = []
    scanned = 0
    for rel, (path, mtime_ns, size) in current.items():
        cached = old_files.get(rel)
        if changed and cached and cached.get("mtime_ns") == mtime_ns and cached.get("size") == size:
            if cached.get("kind") == "markup":
                markup[rel] = cached["summary"]
            elif "facts" in cached:
                files[rel] = cached["facts"]
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            warnings.append(f"{rel}: could not read: {exc}")
            continue
        scanned += 1
        if path.suffix.lower() in MARKUP_EXTENSIONS:
            summary = f"[Markup] {rel} ({len(source.splitlines())} lines - AST Skipped)"
            markup[rel] = summary
            old_files[rel] = {"mtime_ns": mtime_ns, "size": size, "kind": "markup", "summary": summary}
        else:
            facts = extract(path, source)
            files[rel] = facts
            old_files[rel] = {"mtime_ns": mtime_ns, "size": size, "kind": "source", "facts": facts}
            warnings.extend(f"{rel}: {warning}" for warning in facts.get("warnings", []))

    # Remove deleted files from cache and preserve only currently discovered files.
    old_files = {rel: old_files[rel] for rel in current if rel in old_files}
    # Cached facts for unchanged files are loaded above; if the cache entry was absent,
    # parse it now (e.g. a cache created by an interrupted earlier run).
    for rel, (path, mtime_ns, size) in current.items():
        if rel in files or rel in markup:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            warnings.append(f"{rel}: could not read: {exc}")
            continue
        scanned += 1
        if path.suffix.lower() in MARKUP_EXTENSIONS:
            summary = f"[Markup] {rel} ({len(source.splitlines())} lines - AST Skipped)"
            markup[rel] = summary
            old_files[rel] = {"mtime_ns": mtime_ns, "size": size, "kind": "markup", "summary": summary}
        else:
            facts = extract(path, source)
            files[rel] = facts
            old_files[rel] = {"mtime_ns": mtime_ns, "size": size, "kind": "source", "facts": facts}
            warnings.extend(f"{rel}: {warning}" for warning in facts.get("warnings", []))

    context = _render_context(root, files, markup)
    try:
        output_path.write_text(context, encoding="utf-8")
        cache_path.write_text(json.dumps({"version": 1, "files": old_files}, indent=2), encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Cannot write scan output/cache: {exc}") from exc

    total_files = len(files) + len(markup)
    line_count = len(context.splitlines())
    size_bytes = len(context.encode("utf-8"))
    approx_tokens = max(1, len(context) // 4)
    stats = {
        "scanned": scanned,
        "total_files": total_files,
        "lines": line_count,
        "bytes": size_bytes,
        "tokens": approx_tokens,
    }
    return ScanResult(scanned, warnings, changed, stats)


def main(argv: list[str] | None = None) -> int:
    """Run SACK's scan or init command."""
    parser = argparse.ArgumentParser(prog="sack", description="Compact source context for AI-assisted coding.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subs = parser.add_subparsers(dest="command", required=True)
    scan = subs.add_parser("scan", help="generate sack_context.txt")
    scan.add_argument("--root", type=Path, default=Path.cwd(), help="project root")
    scan.add_argument("--changed", action="store_true", help="re-extract only new or modified files using cached mtimes")
    init = subs.add_parser("init", help="generate sack_guardrails.md")
    init.add_argument("--force", action="store_true", help="overwrite existing guardrails")
    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            root = args.root.resolve()
            if not root.is_dir():
                print(f"[!] Not a directory: {root}", file=sys.stderr)
                return 2
            print(f"SACK - Sadaqat Ali Context Hack (v{__version__})")
            res = scan_project(root, changed=args.changed)
            count, warnings, _ = res
            stats = getattr(res, "stats", {})
            mode = "changed-file scan" if args.changed else "full scan"
            size_kb = f"{stats.get('bytes', 0) / 1024:.1f}"
            tokens = stats.get("tokens", 0)
            tokens_str = f"{tokens / 1000:.1f}k" if tokens >= 1000 else str(tokens)
            print(
                f"[+] SACK {mode}: {count} file(s) re-extracted | "
                f"Context: {stats.get('total_files', 0)} file(s), {stats.get('lines', 0)} lines, "
                f"~{tokens_str} tokens ({size_kb} KB) -> {root / CONTEXT_NAME}"
            )
            for warning in warnings:
                print(f"[!] {warning}", file=sys.stderr)
            return 0
        destination = Path.cwd() / GUARDRAILS_NAME
        if destination.exists() and not args.force:
            print("[!] sack_guardrails.md already exists; use 'sack init --force'.", file=sys.stderr)
            return 2
        destination.write_text(GUARDRAILS.strip() + "\n", encoding="utf-8")
        print(f"SACK - Sadaqat Ali Context Hack (v{__version__})")
        print("[+] Successfully generated sack_guardrails.md in project root.")
        return 0
    except OSError as exc:
        print(f"[!] SACK error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
