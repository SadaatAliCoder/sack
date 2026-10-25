# SACK AI Code Generation Guardrails

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

## Node.js & CommonJS
- When using CommonJS, structure exports consistently with `module.exports = { ... }` or named `exports.handler`.
- Prefer asynchronous non-blocking APIs (`fs/promises`, `async/await`) over synchronous blocking calls (`fs.readFileSync`).

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
