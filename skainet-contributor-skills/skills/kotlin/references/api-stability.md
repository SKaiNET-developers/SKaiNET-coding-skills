# API stability

## Binary-compatibility-validator

The Gradle plugin `org.jetbrains.kotlinx.binary-compatibility-validator` is applied in `gradle/libs.versions.toml` (alias `binary-compatibility-validator`). It produces a `<module>/api/<target>.api` dump that records every public declaration the module exports. CI fails when the dump changes without an accompanying update.

### When the build fails on the API check

1. Run `./gradlew :<module>:apiDump` to regenerate the dump.
2. Inspect the diff. The change is intentional only if you added, renamed, or removed a public declaration on purpose.
3. Commit the regenerated `*.api` file in the same change as the source edit. The diff IS the public-API changelog.
4. If the diff is unintentional (you accidentally widened visibility, leaked an internal type), fix the source — don't accept the dump.

### Adding a new public declaration

- Mark it `public` explicitly (explicit-API mode).
- If it's part of a DSL block, annotate with the right `@*Dsl` marker so it's only callable inside the intended scope.
- Run `apiDump`, commit the dump.

### Removing or renaming a public declaration

- This is a binary-compatibility break for downstream consumers (vanniktech maven-publish ships these artifacts).
- Don't do this without a deprecation period unless the codebase is pre-1.0 and the user has accepted the break.
- Deprecation: annotate with `@Deprecated(message = "...", replaceWith = ReplaceWith("..."), level = DeprecationLevel.WARNING)`. Bump to `ERROR` after one minor version.

## `@PublishedApi internal`

`inline fun` bodies are textually inlined into call sites. If an `inline fun` calls an `internal` function, that internal function effectively becomes part of the public API surface — but the compiler refuses to compile unless the internal symbol is annotated `@PublishedApi internal`.

```kotlin
@PublishedApi
internal fun <T : DType> TensorSpec.normalized(name: String, dtype: KClass<T>): TensorSpec = ...
// from: SKaiNET/skainet-lang/skainet-lang-dag/src/commonMain/kotlin/sk/ainet/lang/dag/GraphDsl.kt:259-264
```

Use this annotation only when an `inline fun` actually needs the helper. Don't widen a function to `public` just to satisfy an `inline fun`. Don't apply `@PublishedApi internal` defensively to functions that aren't called from inline code.

## Stability contract for SKaiNET DSL surfaces

- The tensor DSL (`tensor { }`, `data { tensor { } }`), the NN DSL (`sequential { }`), the DAG DSL (`dag { }`), and the test API (`TensorAssertions`, `ToleranceConfig`) are public stable surface — changes here cascade through every consumer.
- DSL marker annotations (`@TensorDsl`, `@NetworkDsl`, `@DagDsl`) gate scope leakage and are part of the contract.
- Internal lowerings (`NeuralNetworkDslImpl`, `DagBuilder` internals, `TensorDefineDslImpl`) are NOT stable — they may be refactored without an API bump.
