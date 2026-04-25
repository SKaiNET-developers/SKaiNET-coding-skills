---
name: skainet-java-interop
description: Use ONLY when designing or editing the Java-facing facade INSIDE the SKaiNET repository — files under `SKaiNET/skainet-*/src/jvmMain/kotlin/sk/ainet/java/`. Trigger tokens include `@file:JvmName`, `@JvmStatic`, `@JvmOverloads`, `package sk.ainet.java`, `object SKaiNET`, `object TensorJavaOps`. Encodes the contributor-side rules for the convention. Do NOT fire when the user is CALLING the Java facade from a Java app — that's the consumer-side `skainet-java-consumer` skill.
version: 0.1.0
---

# skainet-java-interop

Rules for making SKaiNET features usable from Java without surfacing Kotlin-specific machinery. Java is the first guest language after Kotlin, so its ergonomics are a constraint — not an afterthought.

## When to use

- Adding a new Java-callable surface (factory, ops utility, builder).
- Editing files under `skainet-*/src/jvmMain/kotlin/sk/ainet/java/`.
- Reviewing whether a Kotlin API can be called idiomatically from Java.
- Porting a Kotlin test into the `skainet-test-java` module to prove the Java surface.

## When NOT to use

- Writing the underlying Kotlin implementation — `kotlin`.
- Editing tests against the Java surface — `skainet-testing` (the Java JUnit pattern is documented there).
- Picking the source set or KMP target — `kmp`.
- Adding the Gradle dependency on `skainet-test-java` — `gradle-multimodule`.

## Hard rules

1. **`@file:JvmName("...")` on every Java-callable file.** The file's first non-blank line MUST be `@file:JvmName("...")` followed by `package sk.ainet.java`. The JvmName matches what Java users will type as the class identifier (`SKaiNET`, `TensorJavaOps`, `<Feature>JavaOps`).
2. **Container shape is `object`, never top-level functions.** A Java-callable surface MUST be `public object Name { ... }`. Never expose top-level `public fun foo(...)` to Java callers — Java sees them as static methods on a synthetic `<FileName>Kt` class.
3. **Every member carries `@JvmStatic`.** Without it, Java users have to type `SKaiNET.INSTANCE.context()` instead of `SKaiNET.context()`. This rule applies to every public function and every property accessor on the Java-facing object.
4. **Default arguments require `@JvmOverloads`.** Java doesn't see Kotlin defaults; `@JvmOverloads` synthesises overloads with progressively fewer parameters from right to left. Apply it to every `@JvmStatic` function that has a default value.
5. **Forbidden in Java-facing signatures**:
   - `value class` types (Java sees the boxed form, defeats the purpose)
   - `inline fun` (the bytecode shape is unfriendly)
   - `Result<T>` (no Kotlin runtime in pure Java contexts; consumers can't unwrap)
   - Receiver-typed lambdas (`X.() -> Y`) — Java users cannot supply them
   - `Sequence<T>` (no Java-native iteration); use `Iterable<T>` or a primitive array instead
   - Variance tokens that complicate Java generics — flatten to `Tensor<*, *>` for any tensor crossing the boundary
6. **Tensors crossing the boundary use `Tensor<*, *>`.** Java callers cannot easily express `Tensor<DType, Any?>` parameters; expose `Tensor<*, *>` and cast internally with `@Suppress("UNCHECKED_CAST")`. See `TensorJavaOps.add` for the canonical pattern.
7. **Primitive arrays beat `List<Float>`.** Use `FloatArray`, `IntArray`, `DoubleArray`, `ByteArray` — Java sees them as primitive arrays (`float[]`, `int[]`, …), zero boxing.
8. **DType is passed by instance, not `KClass`.** Java callers don't have ergonomic access to `KClass<T>`; expose `DType` instances (`DType.fp32()`, `DType.int32()`) and resolve to `KClass` internally.
9. **`@JvmOverloads` for any defaults; no `vararg` of objects in Java-facing positions** unless backed by a primitive array.
10. **Mirror every Java-facing method with a Java JUnit 5 test in `skainet-test-java`.** The presence of a test in that module is the canonical proof that Java consumers can call the API. New `@JvmStatic` member ⇒ new `@Test` in `skainet-test-java`.

## Workflow

1. Find the closest sibling under `skainet-*/src/jvmMain/kotlin/sk/ainet/java/`. Mirror its `@file:JvmName`, package declaration, KDoc-with-Java-example header, and member shape.
2. Define the new `object` (or extend an existing one).
3. For each member: `@JvmStatic` is mandatory; `@JvmOverloads` if any parameter has a default; primitive arrays for bulk data; `Tensor<*, *>` for tensors crossing the boundary.
4. Implement the member by casting the wildcard tensor to the internal generic form (`Tensor<DType, Any?>`) and delegating to the Kotlin API.
5. Write a JUnit 5 test under `skainet-test-java/src/test/java/sk/ainet/java/<Feature>JavaOpsTest.java` proving the surface compiles and runs from Java.
6. Self-verify with the checklist below before reporting done.

## Self-verification checklist

Before declaring the change complete:

- [ ] File starts with `@file:JvmName("...")` (line 1).
- [ ] File is in `package sk.ainet.java`.
- [ ] Container is a `public object`.
- [ ] Every public member has `@JvmStatic`.
- [ ] Every member with a default has `@JvmOverloads`.
- [ ] No `value class`, no `Result<T>`, no `Sequence<T>`, no receiver-typed lambdas in any signature.
- [ ] Tensors cross the boundary as `Tensor<*, *>`.
- [ ] DType crosses as `DType` instance, not `KClass<DType>`.
- [ ] A JUnit 5 test exists under `skainet-test-java/.../<Feature>JavaOpsTest.java` exercising at least one method of the new surface.

## Canonical examples

**Entry-point factory:**

```kotlin
@file:JvmName("SKaiNET")

package sk.ainet.java

import sk.ainet.context.DirectCpuExecutionContext
import sk.ainet.context.ExecutionContext
import sk.ainet.lang.tensor.Shape
import sk.ainet.lang.tensor.Tensor
import sk.ainet.lang.types.DType
import sk.ainet.lang.types.FP32
import kotlin.reflect.KClass

public object SKaiNET {

    @JvmStatic
    public fun context(): ExecutionContext =
        DirectCpuExecutionContext.create()

    @JvmStatic
    public fun tensor(ctx: ExecutionContext, shape: IntArray, dtype: DType, data: FloatArray): Tensor<*, *> {
        @Suppress("UNCHECKED_CAST")
        val kclass = dtype::class as KClass<DType>
        return ctx.fromFloatArray<DType, Any?>(Shape(*shape), kclass, data)
    }

    @JvmStatic
    @JvmOverloads
    public fun zeros(ctx: ExecutionContext, shape: IntArray, dtype: DType = FP32): Tensor<*, *> {
        @Suppress("UNCHECKED_CAST")
        val kclass = dtype::class as KClass<DType>
        return ctx.zeros<DType, Any?>(Shape(*shape), kclass)
    }
}
// from: SKaiNET/skainet-backends/skainet-backend-cpu/src/jvmMain/kotlin/sk/ainet/java/SKaiNET.kt:1-102
```

**Ops facade — every member `@JvmStatic`, defaults via `@JvmOverloads`:**

```kotlin
@file:JvmName("TensorJavaOps")

package sk.ainet.java

public object TensorJavaOps {

    @JvmStatic
    public fun add(a: Tensor<*, *>, b: Tensor<*, *>): Tensor<*, *> {
        @Suppress("UNCHECKED_CAST")
        val ta = a as Tensor<DType, Any?>
        @Suppress("UNCHECKED_CAST")
        val tb = b as Tensor<DType, Any?>
        return ta.ops.add(ta, tb)
    }

    @JvmStatic
    public fun matmul(a: Tensor<*, *>, b: Tensor<*, *>): Tensor<*, *> { /* ... */ }

    @JvmStatic
    @JvmOverloads
    public fun softmax(a: Tensor<*, *>, dim: Int = -1): Tensor<*, *> { /* ... */ }
}
// from: SKaiNET/skainet-lang/skainet-lang-core/src/jvmMain/kotlin/sk/ainet/java/TensorJavaOps.kt:1-322
```

**Mirror Java JUnit test that proves the surface from a Java caller:**

```java
package sk.ainet.java;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import sk.ainet.context.ExecutionContext;
import sk.ainet.lang.tensor.Tensor;
import sk.ainet.lang.types.DType;

import static org.junit.jupiter.api.Assertions.*;

class TensorJavaOpsTest {
    private static ExecutionContext ctx;

    @BeforeAll
    static void setUp() { ctx = SKaiNET.context(); }

    @Test
    void add() {
        Tensor<?, ?> a = SKaiNET.tensor(ctx, new int[]{2, 2}, DType.fp32(),
                new float[]{1f, 2f, 3f, 4f});
        Tensor<?, ?> b = SKaiNET.tensor(ctx, new int[]{2, 2}, DType.fp32(),
                new float[]{10f, 20f, 30f, 40f});

        Tensor<?, ?> c = TensorJavaOps.add(a, b);
        assertArrayEquals(new int[]{2, 2}, c.getShape().getDimensions());

        float[] result = c.getData().copyToFloatArray();
        assertArrayEquals(new float[]{11f, 22f, 33f, 44f}, result, 1e-6f);
    }
}
// from: SKaiNET/skainet-test/skainet-test-java/src/test/java/sk/ainet/java/TensorJavaOpsTest.java:1-38
```

## Related skills

- The underlying Kotlin API the facade wraps — see [`../kotlin/SKILL.md`](../kotlin/SKILL.md).
- Source-set placement (always `jvmMain` for facades) — see [`../kmp/SKILL.md`](../kmp/SKILL.md).
- Wiring `skainet-test-java` and adding the Java test — see [`../gradle-multimodule/SKILL.md`](../gradle-multimodule/SKILL.md) and [`../skainet-testing/SKILL.md`](../skainet-testing/SKILL.md).
- Tensor construction the facade exposes — see the `skainet-data-dsl` skill (in the sibling consumer plugin).
- The Java caller's perspective on this same surface — see the `skainet-java-consumer` skill (in the sibling consumer plugin).

## Anti-patterns

```kotlin
// WRONG — top-level fun; Java sees it as TensorOpsKt.add
@file:JvmName("TensorOps")
package sk.ainet.java

public fun add(a: Tensor<*, *>, b: Tensor<*, *>): Tensor<*, *> = ...
```
```kotlin
// RIGHT — public object + @JvmStatic
@file:JvmName("TensorJavaOps")
package sk.ainet.java

public object TensorJavaOps {
    @JvmStatic
    public fun add(a: Tensor<*, *>, b: Tensor<*, *>): Tensor<*, *> = ...
}
```

```kotlin
// WRONG — defaults without @JvmOverloads; Java cannot omit `dim`
@JvmStatic
public fun softmax(a: Tensor<*, *>, dim: Int = -1): Tensor<*, *> = ...
```
```kotlin
// RIGHT — @JvmOverloads
@JvmStatic
@JvmOverloads
public fun softmax(a: Tensor<*, *>, dim: Int = -1): Tensor<*, *> = ...
```

```kotlin
// WRONG — exposing KClass to Java
@JvmStatic
public fun tensor(ctx: ExecutionContext, shape: IntArray, dtype: KClass<DType>, data: FloatArray): Tensor<*, *> = ...
```
```kotlin
// RIGHT — DType instance
@JvmStatic
public fun tensor(ctx: ExecutionContext, shape: IntArray, dtype: DType, data: FloatArray): Tensor<*, *> = ...
```

```kotlin
// WRONG — Sequence + receiver lambda
@JvmStatic
public fun forEachLayer(model: Module<*, *>, action: Module<*, *>.(Layer) -> Unit)
```
```kotlin
// RIGHT — plain Iterable + java.util.function.BiConsumer (or specialised interface)
@JvmStatic
public fun forEachLayer(model: Module<*, *>, action: java.util.function.BiConsumer<Module<*, *>, Layer>)
```

## References

- [`references/jvm-annotations.md`](references/jvm-annotations.md) — every `@Jvm*` annotation we use, when to apply each.
- [`references/forbidden-signatures.md`](references/forbidden-signatures.md) — exhaustive list of Kotlin shapes that MUST NOT cross the Java boundary, with rewrites.
