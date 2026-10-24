# SACK — Sadaqat Ali Context Hack

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#)
[![Version](https://img.shields.io/badge/version-0.5.0-orange.svg)](#)

A zero-runtime-dependency CLI that builds a **compact, high-density structural context index** for AI-assisted software development.

Feeding entire source trees to LLMs (Claude, GPT-4o, Gemini, DeepSeek, Cursor) burns tens of thousands of tokens on implementation details, markup, and boilerplate. **SACK** extracts public APIs, types, signatures, dependency graphs, and framework-level contracts—slashing token consumption by **80–90%** while giving AI models exact architectural clarity.

---

## ⚡ Key Features

- **14+ Languages & Stacks**: Python (AST-grade), TypeScript, JavaScript, Svelte (4 & 5), Vue, Flutter/Dart, Rust, Go, C/C++, Java, PHP, C#, Kotlin, Swift, and Ruby.
- **Framework & IPC Intelligence**:
  - **Svelte**: Extracts Svelte 4 props, Svelte 5 Runes (`$props()`, `$state()`, `$derived()`), emitted events, and **Tauri IPC** calls (`invoke`, `listen`, `emit`).
  - **Rust**: Preserves attributes such as `#[tauri::command]` and `#[derive(...)]`.
  - **Flutter & Dart**: Extracts widgets, constructors, null-safety types, annotations (`@override`, `@immutable`), and resolves `package:...` imports.
  - **C# / .NET**: Extracts classes, interfaces, records, methods, and attributes (`[ApiController]`, `[HttpGet]`).
  - **Kotlin**: Data classes, suspend functions, and `@Composable` annotations.
  - **Swift**: Structs, protocols, and property wrappers (`@State`, `@Binding`).
- **Dependency Topology Graph**: Automatically maps project-relative internal imports into a dependency overview.
- **Smart Filtering**: Automatically ignores build artifacts, minified files (`*.min.js`), and machine-generated code (`*.g.dart`, `*.designer.cs`, `*.pb.go`).
- **Token & Size Metrics**: Reports lines, kilobytes, and approximate token counts on every scan.
- **Incremental Caching**: `--changed` flag re-indexes only modified files using local mtime caches (`.sack_cache.json`).
- **AI Coding Guardrails**: Generates `sack_guardrails.md` tailored with language-specific best practices for LLMs.
- **Zero Runtime Dependencies**: Built entirely with Python's standard library.

---

## 🚀 Installation

Install directly from checkout or local clone:

```bash
git clone https://github.com/your-username/sack.git
cd sack
python -m pip install .
```

For development in editable mode:
```bash
python -m pip install -e .
```

---

## 🛠️ Commands

| Command | Description |
| :--- | :--- |
| `sack scan` | Full scan of current directory, updates cache, and generates `sack_context.txt`. |
| `sack scan --changed` | Re-extracts only new or modified files using cached mtimes; preserves unchanged files. |
| `sack scan --root /path` | Scans a specified project root directory. |
| `sack init` | Creates `sack_guardrails.md` with language-specific rules for AI models. |
| `sack init --force` | Overwrites existing `sack_guardrails.md`. |
| `sack --version` | Displays current SACK version. |

---

## 📋 Supported Languages & Capabilities

| Language / Stack | File Extensions | Extracted Elements |
| :--- | :--- | :--- |
| **Python** | `.py` | AST parsing, multiline signatures, types, decorators, docstrings |
| **JavaScript / TypeScript** | `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs` | Imports, interfaces, types, enums, classes, arrow functions, JSDoc |
| **Svelte** | `.svelte` | Svelte 4 props, Svelte 5 Runes (`$props`, `$state`, `$derived`), Tauri IPC (`invoke`), events |
| **Vue** | `.vue` | `<script>` & `<script setup lang="ts">` declarations, imports |
| **Flutter & Dart** | `.dart` | Classes, widgets, constructors, functions, `@override`, `package:...` resolution |
| **Rust** | `.rs` | Functions, structs, traits, `#[tauri::command]` and attributes |
| **C#** | `.cs` | `using`, namespaces, classes, interfaces, records, attributes (`[Route]`) |
| **Kotlin** | `.kt`, `.kts` | `package`, data classes, suspend functions, `@Composable` |
| **Swift** | `.swift` | Structs, protocols, functions, `@State`, `@Binding`, property wrappers |
| **Ruby** | `.rb` | `require`, classes, modules, methods (`def`), constants |
| **Go** | `.go` | Packages, imports, structs, interfaces, functions |
| **C / C++** | `.c`, `.cpp`, `.h`, `.hpp`, etc. | Headers, classes, templates, function prototypes |
| **Java** | `.java` | Packages, imports, classes, interfaces, records, annotations |
| **PHP** | `.php` | Namespaces, classes, interfaces, traits, methods, PHPDoc |
| **Markup & Styles** | `.html`, `.css`, `.scss` | High-level line summaries (omits noisy DOM/CSS) |

---

## 🤖 How to Use with AI Models

When asking an AI model (ChatGPT, Claude, Gemini, Cursor) to write or refactor code in your project:

1. Run `sack scan` in your project root to generate `sack_context.txt`.
2. Attach or paste `sack_context.txt` into your prompt:

```text
Here is the structural context index of my project generated by SACK:

<context>
[PASTE sack_context.txt HERE]
</context>

Task: Add a new user profile settings feature.
Follow the architectural patterns and existing APIs outlined in the context above.
```

The AI model receives complete awareness of existing component APIs, Tauri IPC calls, and dependency graphs—without filling up context limits.

---

## 🛡️ AI Guardrails (`sack init`)

Run `sack init` to create a `sack_guardrails.md` file in your repository. This file instructs AI models on universal and language-specific coding standards (PEP 257 for Python, sound null safety for Dart/Flutter, strict IPC typing for Tauri, const constructors, etc.).

---

## 📄 License

GNU General Public License v3.0 (GPL-3.0) © 2026 Sadaqat Ali. See [LICENSE](LICENSE) for details.
