# Forbidden signatures across the Java boundary

Anything in this list MUST NOT appear in a `@JvmStatic` function exposed by a `sk.ainet.java` `object`. The right-hand column shows the rewrite.

| Forbidden | Why | Rewrite |
|---|---|---|
| `value class FooId` parameter | Java sees the wrapped primitive boxed; loses the type-safety reason for the value class. | Take the underlying primitive directly (`String` / `Long`). Document in KDoc that Kotlin callers should pass the value-class form. |
| `Result<T>` return | No idiomatic unwrapping in Java. | Throw on failure (with `@Throws(...)` if checked) and return `T` on success. |
| `Sequence<T>` parameter or return | No native Java iteration; consumers can't drive a `Sequence`. | `Iterable<T>` parameter; `List<T>` return. |
| `T.() -> R` (receiver-typed lambda) | Java cannot supply a receiver-typed lambda. | Plain `(T) -> R` (i.e. `Function1<T, R>`) or a SAM interface (`java.util.function.Function`, `BiConsumer`, etc.). |
| `T.() -> Unit` (configuration lambda) | Same as above; common DSL pattern. | A builder class with explicit setters that returns `this`. |
| `KClass<T>` parameter | No idiomatic Java way to obtain a `KClass<T>`. | Pass the typed instance: `DType` instead of `KClass<DType>`; `Class<T>` if a class token is unavoidable. |
| `inline fun <reified T>` | Reification disappears in Java; the bytecode shape is unfriendly. | Non-inline function that takes `Class<T>`. |
| `vararg T` for object types | Java sees `T[]` but boxing kills perf for primitives. | Primitive array (`FloatArray`, `IntArray`) or explicit `List<T>`. |
| `Pair<A, B>` / `Triple<A, B, C>` | Awkward to construct from Java (`new Pair<>(a, b)` is ugly and imports `kotlin.Pair`). | Two-arg / three-arg overloads with separate parameters. |
| `ULong`, `UInt`, `UByte`, `UShort` | Java has no unsigned primitives. | Signed counterparts; document the wrap-around behaviour. |
| `internal` visibility on a `@JvmStatic` member | The member is exposed to Java with name mangling — confusing. | `public`. |
| `suspend fun` | Java cannot call coroutines. | Block-and-throw on the JVM (`runBlocking { ... }`) ONLY if the operation is short; otherwise return a `CompletableFuture<T>` (Java 8+) or a callback. |
| `Flow<T>` return | No Java consumer for Kotlin flows. | `java.util.concurrent.Flow.Publisher<T>` (JDK 9+) or callback-based subscription. |
| Generics with implicit declaration-site variance | Java users see raw types or have to write awkward bounds. | Project to a wildcard at the boundary (`Tensor<*, *>` is the canonical example). |

## Tensor convention

Tensors crossing the Java boundary are ALWAYS `Tensor<*, *>`. Internally cast back with `@Suppress("UNCHECKED_CAST")`:

```kotlin
@JvmStatic
public fun add(a: Tensor<*, *>, b: Tensor<*, *>): Tensor<*, *> {
    @Suppress("UNCHECKED_CAST")
    val ta = a as Tensor<DType, Any?>
    @Suppress("UNCHECKED_CAST")
    val tb = b as Tensor<DType, Any?>
    return ta.ops.add(ta, tb)
}
// from: SKaiNET/skainet-lang/skainet-lang-core/src/jvmMain/kotlin/sk/ainet/java/TensorJavaOps.kt:28-35
```

This is the only place `@Suppress("UNCHECKED_CAST")` is acceptable in this project — at the Java/Kotlin boundary.

## DType convention

`DType` is passed by instance:

- `DType.fp32()` returns the `FP32` instance.
- `DType.int32()` returns the `Int32` instance.
- `DType.int8()` returns the `Int8` instance.

Internally, the facade resolves the instance back to a `KClass<DType>` for the Kotlin API:

```kotlin
@Suppress("UNCHECKED_CAST")
val kclass = dtype::class as KClass<DType>
```

Do not expose `KClass<DType>` to Java — it's a hostile parameter type for Java callers.

## Bulk data convention

| Internally | Across boundary |
|---|---|
| `List<Float>` | `FloatArray` (Java sees `float[]`) |
| `List<Int>` | `IntArray` |
| `List<Double>` | `DoubleArray` |
| `List<Byte>` | `ByteArray` |

Avoid `List<T>` for hot paths; primitive arrays remove boxing overhead and read naturally from Java.
