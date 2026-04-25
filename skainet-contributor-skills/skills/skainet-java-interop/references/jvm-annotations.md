# JVM annotations cheat sheet

## `@file:JvmName("...")`

File-level annotation that renames the synthetic class Kotlin generates from a file. Without it, Java sees `<FileName>Kt`.

```kotlin
@file:JvmName("TensorJavaOps")
package sk.ainet.java
```

When the file contains an `object`, the JvmName SHOULD match the object's name — Java callers then use one identifier for both file references and `import` statements.

## `@JvmStatic`

Member annotation on `object` or `companion object` that emits a real JVM `static` method. Without it, Java callers go through `<Object>.INSTANCE.method()`.

```kotlin
public object SKaiNET {
    @JvmStatic
    public fun context(): ExecutionContext = ...
}
```

Java: `SKaiNET.context()` ✓
Without `@JvmStatic`: `SKaiNET.INSTANCE.context()` ✗

## `@JvmOverloads`

Generates JVM overloads with progressively fewer right-to-left parameters for any function with default values.

```kotlin
@JvmStatic
@JvmOverloads
public fun zeros(ctx: ExecutionContext, shape: IntArray, dtype: DType = FP32): Tensor<*, *>
```

Java: `SKaiNET.zeros(ctx, new int[]{2, 2})` AND `SKaiNET.zeros(ctx, new int[]{2, 2}, DType.fp32())` ✓
Without it: only the 3-arg overload exists.

## `@JvmField`

Removes the property accessor wrapper, exposing the field directly. Use only for `const`-like values where the property nature is meaningless.

```kotlin
public object Defaults {
    @JvmField
    public val DEFAULT_TOLERANCE: Float = 1e-5f
}
```

Java: `Defaults.DEFAULT_TOLERANCE` (not `Defaults.getDEFAULT_TOLERANCE()`).

`@JvmField` is unusual on a Java-friendly facade — most state is encapsulated. Use sparingly.

## `@JvmName("...")` on a member

Renames a single function or property accessor without renaming the file. Useful when an idiomatic Kotlin name collides with a Java keyword or has unfortunate JVM mangling.

```kotlin
@JvmStatic
@JvmName("matMul")
public fun matmul(a: Tensor<*, *>, b: Tensor<*, *>): Tensor<*, *>
```

Avoid unless there's a reason. Consistent naming across Kotlin and Java is preferable.

## `@Throws(...)`

Declares checked exceptions on a function that Java callers must `try`/`catch`. Kotlin does not have checked exceptions, so without this annotation Java sees an unchecked surface.

```kotlin
@JvmStatic
@Throws(IOException::class)
public fun loadModel(path: String): Tensor<*, *> = ...
```

Apply to functions that can throw IO / parse / format exceptions and Java callers SHOULD handle.

## What we DO NOT use

- **`@JvmMultifileClass`** — splits one JVM class across multiple Kotlin files. Adds confusion; we use one `object` per file.
- **`@JvmDefault` / `@JvmDefaultWithCompatibility`** — interface default methods. The Java-facing surface is `object`s, not interfaces.

## Combining annotations

Order is irrelevant for the compiler, but be consistent within a file. The convention in `skainet-backend-cpu`:

```
@JvmStatic
@JvmOverloads
public fun ...
```

Function-level annotations always above the visibility modifier.
