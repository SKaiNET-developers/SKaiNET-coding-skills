# Tensor builders

Authoritative source: `SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/dsl/TensorDSL.kt`. Update when signatures drift.

## Top-level entry points

```kotlin
public fun <T : DType, V> tensor(
    executionContext: ExecutionContext,
    dtype: KClass<T>,
    content: TensorDefineDsl<T, V>.() -> Tensor<T, V>
): Tensor<T, V>
// from: TensorDSL.kt:18-25
```

`data<T, V>(ctx) { tensor { shape(...) { ... } } }` is the phase-aware variant defined in `sk.ainet.context` (separate import: `sk.ainet.context.data`). Its `executionContext` parameter defaults to `DefaultDataExecutionContext()`. Related entry points in the same file (`ContextDsl.kt:19-53`):

```kotlin
public fun data(executionContext: ExecutionContext = DefaultDataExecutionContext(),
                content: DataContextDsl.(executionContext: ExecutionContext) -> Unit)  // untyped block form

public inline fun <reified T : DType, V> data(
    executionContext: ExecutionContext = DefaultDataExecutionContext(),
    noinline content: TypedDataContextDsl<T, V>.(executionContext: ExecutionContext) -> Tensor<T, V>
): Tensor<T, V>

public fun createDataMap(executionContext: ExecutionContext = DefaultDataExecutionContext(),
                         content: DataContextDsl.(executionContext: ExecutionContext) -> Unit
): Map<String, Tensor<*, *>>  // every tensor in the block must use the named tensor(name) { } overload
```

Inside a `data { }` block, `DataContextDsl` (in `sk.ainet.lang.tensor.dsl.DataContextDsl`) additionally offers `scalar(value)`, `vector(length) { ... }`, `matrix(rows, columns) { ... }` and a named `tensor(name) { ... }` overload — all with reified-dtype convenience wrappers.

## `TensorDefineDsl<T, V>`

```kotlin
public fun tensor(content: TensorFactoryContext<T, V>.() -> Tensor<T, V>): Tensor<T, V>
// from: TensorDSL.kt:30
```

The inner `tensor { ... }` block reads the `TensorFactoryContext` so the user can call `shape(...)`. The double naming is intentional: outer `tensor` means "produce a tensor", inner `tensor` means "build it with a shape literal".

## `TensorFactoryContext.shape(...)`

```kotlin
public fun shape(vararg dimensions: Int, init: TensorCreationScope<T, V>.(Shape) -> Tensor<T, V>): Tensor<T, V>
public fun shape(shape: Shape, init: TensorCreationScope<T, V>.(Shape) -> Tensor<T, V>): Tensor<T, V>
// from: TensorDSL.kt:129-139
```

Two forms — varargs for inline literals (`shape(2, 3) { ... }`), `Shape` overload for prebuilt shape values.

## `TensorCreationScope<T, V>` — fills

```kotlin
public fun zeros(): Tensor<T, V>
public fun ones(): Tensor<T, V>
public fun full(value: Number): Tensor<T, V>

public fun from(vararg data: Float): Tensor<T, V>
public fun fromList(data: List<Float>): Tensor<T, V>
public fun fromArray(data: FloatArray): Tensor<T, V>

public fun from(vararg data: Int): Tensor<T, V>
public fun fromIntList(data: List<Int>): Tensor<T, V>
public fun fromArray(data: IntArray): Tensor<T, V>
// from: TensorDSL.kt:56-73
```

`require` enforces `data.size == shape.volume` for `from*` overloads. Mismatch throws at runtime with a descriptive message.

## `TensorCreationScope<T, V>` — random and custom

```kotlin
public fun init(generator: (indices: IntArray) -> V): Tensor<T, V>
public fun randomInit(generator: (random: Random) -> V, random: Random = Random.Default): Tensor<T, V>

public fun randn(mean: Float = 0.0f, std: Float = 1.0f, random: Random = Random.Default): Tensor<T, V>
public fun randN(mean: Float = 0.0f, std: Float = 1.0f, random: Random = Random.Default): Tensor<T, V>  // legacy alias
public fun uniform(min: Float = 0.0f, max: Float = 1.0f, random: Random = Random.Default): Tensor<T, V>

public fun random(initBlock: (Shape) -> Tensor<T, V>): Tensor<T, V>  // escape hatch for custom distributions
// from: TensorDSL.kt:76-107
```

Pass `Random(seed)` for reproducible tests; default `Random.Default` is fine for examples.

## `TensorBuilder<T, V>` and `ShapeBuilder<T, V>` — staged form

For producing a `TensorInitializer` you can call `.build(ctx)` on later (rare; useful in code generators):

```kotlin
TensorBuilder<FP32, Float>(FP32::class)
    .shape(2, 3)
    .ones()              // returns TensorInitializer
    .build(ctx)          // materialises to Tensor<FP32, Float>
// from: TensorDSL.kt:145-267
```

Staged form is a substitute for the DSL when you can't run the lambda eagerly (KSP code generation). For everyday code, prefer the DSL form.

## `InitializationType<V>`

```kotlin
public sealed class InitializationType<out V> {
    public object Zeros : InitializationType<Nothing>()
    public object Ones : InitializationType<Nothing>()
    public data class Fill<V>(val value: Number) : InitializationType<V>()
    public data class Normal<V>(val mean: Float, val std: Float, val random: Random) : InitializationType<V>()
    public data class Uniform<V>(val min: Float, val max: Float, val random: Random) : InitializationType<V>()
    public data class Custom<V>(val generator: (indices: IntArray) -> V) : InitializationType<V>()
    public data class RandomCustom<V>(val generator: (random: Random) -> V, val random: Random) : InitializationType<V>()
}
// from: TensorDSL.kt:272-281
```

The sealed hierarchy is what `TensorInitializer.build(ctx)` switches on. Generally consumed internally; included here so the agent recognises every init flavour the system supports.

## Slicing — `TensorSliceBuilder<T, V>`

```kotlin
public class TensorSliceBuilder<T : DType, V> {
    public fun segment(block: SegmentBuilder<T, V>.() -> Slice<T, V>)
}
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/TensorSliceBuilder.kt:31-53
```

`SegmentBuilder` exposes `range(start, end)`, `at(index)`, `all()`, `step(start, end, step)`. The number of `segment { }` calls must equal `tensor.shape.rank`.

## Choosing a dtype + value-type

The pair `<T, V>` must be consistent. `DType` is a sealed interface with fourteen `object` members (`sk.ainet.lang.types.DType.entries`); the value-type mapping follows `DType.kotlinClass()` in `sk.ainet.lang.types.DTypeExtensions.kt:5-20`:

| `T` | `V` |
|---|---|
| `FP32` | `Float` |
| `FP64` | `Double` |
| `FP16` | `Float` |
| `BF16` | `Float` |
| `Int8` | `Byte` |
| `Int16` | `Short` |
| `Int32` | `Int` |
| `Int64` | `Long` |
| `Int4` | `Byte` |
| `UInt8` / `UInt16` / `UInt32` / `UInt64` | `UByte` / `UShort` / `UInt` / `ULong` |
| `Ternary` | `Byte` (as used by `Tensor<Ternary, Byte>` call sites) |
