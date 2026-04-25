---
name: kotlin
description: Use ONLY when editing Kotlin (`.kt`) source files INSIDE the SKaiNET repository (i.e. you're contributing to SKaiNET itself, not consuming it as a library). Enforces project idioms: explicit-API mode, package layout under `sk.ainet.*`, sealed hierarchies, `value class` for type-safe wrappers, no Java-style getters in Kotlin code. Do NOT fire when the user is writing application code that depends on SKaiNET as a library — that's the consumer plugin's territory. Does not fire on DSL invocation sites, build files, or test files within SKaiNET either (those are covered by other contributor skills).
version: 0.1.0
---

# kotlin

Idiomatic Kotlin coding rules for production code in SKaiNET. Covers package layout, API stability, nullability, sealed hierarchies, and the `expect`/`actual` boundary. Style topics that are project-specific.

## When to use

- Editing or adding a `.kt` file under any module's `commonMain/`, `jvmMain/`, or platform-specific main source set.
- Reviewing whether a public API is shaped correctly (explicit visibility, no leaked Java-style getters, correct `@PublishedApi` discipline).
- Deciding whether something should be a `data class`, `value class`, `sealed class`, `sealed interface`, or `object`.

## When NOT to use

- Writing inside a `tensor { }`, `pipeline<...>()`, `sequential<...> { }`, or `dag { }` block — those are the DSL skills.
- Editing `build.gradle.kts`, `settings.gradle.kts`, `libs.versions.toml`, or files under `build-logic/` — that's `gradle-multimodule`.
- Writing tests — that's `skainet-testing`.
- Deciding which source set a file belongs in — that's `kmp`.

## Hard rules

1. **`explicitApi()` is on for every `kotlin { }` block in this project.** Every public top-level declaration MUST carry an explicit visibility modifier (`public`, `internal`, `private`). Do not write `fun foo()` at top level — write `public fun foo()` or `internal fun foo()`.
2. **Package layout is `sk.ainet.<area>[.<sub-area>]`.** New files MUST live under `src/<sourceset>/kotlin/sk/ainet/...`. Do not introduce new top-level packages.
3. **No Java-style getters.** Expose Kotlin properties (`val`, `var`) — never `getFoo()` / `setFoo()` on a Kotlin class. Java consumers reach Kotlin through the dedicated facades in `sk/ainet/java/` (covered by `skainet-java-interop`).
4. **`value class` for any wrapper around a primitive that has semantic meaning** (e.g. tensor IDs, layer names, axis indices). Not for things that need equality on multiple fields — those are `data class`.
5. **Sealed hierarchies for closed sets of variants.** Initialization strategies, layer kinds, dtype tags use `sealed class` / `sealed interface`. Do not use `enum class` if the variants carry data (see `InitializationType` in `TensorDSL.kt`).
6. **Nullability is meaningful.** A non-null type means "always present"; a `T?` type means "callers must handle absence." Never use `!!` to silence the compiler outside a documented invariant — prefer `requireNotNull(x) { "<reason>" }` so the failure is loud.
7. **Coroutines are structured.** Suspend functions belong on a `CoroutineScope` provided by the caller; never launch into `GlobalScope`. Hot streams use `Flow`; cold one-shot APIs use suspend functions.
8. **Public-API additions are gated by binary-compatibility-validator.** When the build fails because `*.api` changed, regenerate the dump (`./gradlew apiDump`) and own the change in the same commit — don't suppress the check.
9. **`@PublishedApi internal` is the only way to expose internals to inline functions.** Don't widen visibility just to satisfy `inline fun`.

## Workflow

1. Locate the right file: open the existing `sk.ainet.<area>` package the change belongs to. Don't create a new package without strong justification.
2. Decide the right shape: data class, value class, sealed hierarchy, object, or plain function. Match what surrounding code already does.
3. Write the declaration with explicit visibility. Add KDoc only when the *why* isn't obvious from the name.
4. If the type crosses the JVM/Java boundary, hand off to `skainet-java-interop` for the facade — keep the Kotlin definition idiomatic.
5. If the change breaks a `*.api` dump, regenerate it (`./gradlew :module:apiDump`) and include the diff in the same change.

## Canonical examples

**Explicit API + sealed hierarchy** (used for tensor initialisation):

```kotlin
public sealed class InitializationType<out V> {
    public object Zeros : InitializationType<Nothing>()
    public object Ones : InitializationType<Nothing>()
    public data class Fill<V>(val value: Number) : InitializationType<V>()
    public data class Normal<V>(val mean: Float, val std: Float, val random: Random) : InitializationType<V>()
    public data class Uniform<V>(val min: Float, val max: Float, val random: Random) : InitializationType<V>()
    public data class Custom<V>(val generator: (indices: IntArray) -> V) : InitializationType<V>()
    public data class RandomCustom<V>(val generator: (random: Random) -> V, val random: Random) :
        InitializationType<V>()
}
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/dsl/TensorDSL.kt:272-281
```

**Data-shape DSL with explicit visibility on every entry point:**

```kotlin
@TensorDsl
public fun <T : DType, V> tensor(
    executionContext: ExecutionContext,
    dtype: KClass<T>,
    content: TensorDefineDsl<T, V>.() -> Tensor<T, V>
): Tensor<T, V> { ... }
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/dsl/TensorDSL.kt:17-25
```

**Module-level KMP plugins (so explicit-API is enforced):**

```kotlin
kotlin {
    explicitApi()
    // ... targets ...
}
// from: SKaiNET/skainet-lang/skainet-lang-core/build.gradle.kts:14-16
```

## Related skills

- Source-set placement (`commonMain` vs `jvmMain` vs `iosArm64Main`) — see [`../kmp/SKILL.md`](../kmp/SKILL.md).
- Adding the file to a new module or registering it in the build — see [`../gradle-multimodule/SKILL.md`](../gradle-multimodule/SKILL.md).
- Bridging the new declaration to Java consumers — see [`../skainet-java-interop/SKILL.md`](../skainet-java-interop/SKILL.md).

## Anti-patterns

```kotlin
// WRONG — implicit visibility, will fail explicit-API check
fun computeDiff(expected: Float, actual: Float): Float = expected - actual
```
```kotlin
// RIGHT
public fun computeDiff(expected: Float, actual: Float): Float = expected - actual
```

```kotlin
// WRONG — Java-style accessors on a Kotlin class
public class Layer { fun getInChannels(): Int = inChannels }
```
```kotlin
// RIGHT — Kotlin property
public class Layer { public val inChannels: Int get() = ... }
```

```kotlin
// WRONG — variants with payload as enum
public enum class InitKind { ZEROS, ONES, FILL /* value? */ }
```
```kotlin
// RIGHT — sealed hierarchy carries data
public sealed class InitializationType<out V> { ... }
```

```kotlin
// WRONG — `!!` silently asserts a hidden invariant
val x = map[id]!!
```
```kotlin
// RIGHT — surface the invariant in the failure message
val x = requireNotNull(map[id]) { "missing layer id=$id" }
```

## References

- [`references/style-rules.md`](references/style-rules.md) — explicit-API, package, naming, KDoc rules with one-line examples.
- [`references/api-stability.md`](references/api-stability.md) — binary-compatibility-validator workflow and `@PublishedApi` discipline.
