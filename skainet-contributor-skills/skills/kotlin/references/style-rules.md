# Kotlin style rules (project-specific)

## Visibility

- Every `kotlin { }` in this project enables `explicitApi()`. Top-level declarations require an explicit modifier.
- `public` is the default to *write*, but it must appear in the source — the compiler does not assume it.
- Use `internal` aggressively for module-scoped helpers; widen to `public` only when an external module imports the symbol.

## Packages

- All production sources live under `sk.ainet.<area>[.<sub-area>]` matching the directory tree.
- Module → package mapping (the parts that aren't obvious):
  - `skainet-lang-core` → `sk.ainet.lang.tensor`, `sk.ainet.lang.nn`, `sk.ainet.lang.types`, `sk.ainet.context`
  - `skainet-lang-dag` → `sk.ainet.lang.dag`
  - `skainet-data-transform` → `sk.ainet.data.transform`
  - `skainet-test-groundtruth` → `sk.ainet.test.groundtruth`
  - JVM facades for Java consumers → `sk.ainet.java`

## Naming

- Types: `UpperCamelCase`. `Tensor`, `Module`, `ExecutionContext`.
- Functions and properties: `lowerCamelCase`. `assertTensorClose`, `maxAbsDiff`.
- DSL builder factories take the same name as the result they build (`tensor(...)` returns a `Tensor`, `sequential { ... }` returns a `Module`, `dag { ... }` returns a `GraphProgram`). Do not prefix them with `build` / `make` / `create`.
- DSL marker annotations live next to their DSL and end in `Dsl`: `@TensorDsl`, `@NetworkDsl`, `@DagDsl`.

## Type shape

| Need | Use |
|---|---|
| Wrapper around a single primitive with semantic meaning (axis index, layer id) | `value class` |
| Bag of named fields with structural equality | `data class` |
| Closed set of variants that carry data | `sealed class` / `sealed interface` |
| Closed set of variants without data | `enum class` |
| Singleton with state | `object` |
| Static utilities for Java | `object` with `@JvmStatic` (see `skainet-java-interop`) |

## Generics

- `T : DType, V` is the canonical pair across the codebase: `T` is the dtype tag (`FP32`, `FP16`, `Int8`, …) and `V` is its native value (`Float`, `Byte`, …).
- DSL entry points that need to reify the dtype use `inline fun <reified T : DType, V>`. This is why `sequential<FP32, Float> { }` works.
- `KClass<T>` is passed alongside `<reified T>` only when the DSL needs to forward to a non-inline boundary (see `TensorDSL.kt`).

## Nullability

- A `T?` parameter or return means the absence is part of the contract. Document what `null` means in the KDoc.
- Inside a function, prefer early `requireNotNull(x) { "..." }` over `x!!`. The required message becomes the assertion text.
- For callers that genuinely cannot fail, use `T` (non-null). Don't add a `T?` "for safety" — it pushes the null-handling burden onto every caller.

## Coroutines and concurrency

- Suspend functions take a `CoroutineScope` from the caller; never call `GlobalScope.launch` in production code.
- Use `Flow<T>` for streams, suspend functions for one-shot results.
- Tests of suspend code use `runTest { }` from `kotlinx-coroutines-test`.

## KDoc

- Write KDoc for every `public` declaration that adds information beyond the signature.
- Document *why* and *contract*, not *what*. The signature already shows what.
- For DSL entry points, include a runnable usage block in the KDoc — `dag { ... }` and `sequential { ... }` already do this, follow the pattern.
