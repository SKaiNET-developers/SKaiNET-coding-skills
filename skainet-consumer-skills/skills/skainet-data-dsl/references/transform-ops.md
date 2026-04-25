# Transform pipeline operations

Authoritative source: `SKaiNET/skainet-data/skainet-data-transform/src/commonMain/kotlin/sk/ainet/data/transform/TensorTransformDsl.kt` (extension functions on `Transform<I, Tensor<T, V>>`). Update when extensions drift.

## Pattern

A pipeline is a chain of `Transform<In, Out>` values composed by `then`. The DSL exposes one extension per transform; each takes the `ExecutionContext` so the produced tensors live on the right backend.

```kotlin
val preprocess = pipeline<Tensor<FP32, Float>>()
    .rescale(ctx, scale = 255f)
    .normalize(ctx, mean = mean, std = std, channelAxis = -1)
    .unsqueeze(0)

val batch = preprocess(raw)
// from: SKaiNET/skainet-data/skainet-data-transform/src/commonMain/kotlin/sk/ainet/data/transform/TensorTransformDsl.kt:18-23
```

## Available extensions

```kotlin
public fun <I, T : DType, V> Transform<I, Tensor<T, V>>.rescale(
    ctx: ExecutionContext,
    scale: Float = 255f
): Transform<I, Tensor<T, V>>
// `output = input / scale`. Defaults to 255 for image preprocessing.
// from: TensorTransformDsl.kt:47-50

public fun <I, T : DType, V> Transform<I, Tensor<T, V>>.normalize(
    ctx: ExecutionContext,
    mean: FloatArray,
    std: FloatArray,
    channelAxis: Int = -1
): Transform<I, Tensor<T, V>>
// Channel-wise (`output - mean) / std` along `channelAxis`. Default channelAxis = -1 (last).
// from: TensorTransformDsl.kt:34-39

public fun <I, T : DType, V> Transform<I, Tensor<T, V>>.scaleAndShift(
    ctx: ExecutionContext,
    scale: Float,
    offset: Float = 0f
): Transform<I, Tensor<T, V>>
// `output = input * scale + offset`.
// from: TensorTransformDsl.kt:59-63

public fun <I, T : DType, V> Transform<I, Tensor<T, V>>.clamp(
    ctx: ExecutionContext,
    min: Float,
    max: Float
): Transform<I, Tensor<T, V>>
// Restrict values to [min, max].
// from: TensorTransformDsl.kt:72-76
```

`reshape`, `unsqueeze` and friends follow the same pattern — see the source file for the up-to-date list.

## Where the actual transform classes live

The functions above produce instances of `Normalize`, `Rescale`, `ScaleAndShift`, `Clamp`, etc. — concrete classes in the same package. The DSL extensions are the call site; the classes are the implementation.

## When to NOT use a pipeline

- Single transform → just call the underlying op directly (`tensor.ops.divScalar(tensor, 255f)`).
- Variable-shape data per call (e.g. ragged batches) → the pipeline expects a single static input shape; use a custom function.

## Adding a new transform

1. Define a `class NewTransform(ctx: ExecutionContext, ...)` implementing `Transform<Tensor<T, V>, Tensor<T, V>>`.
2. Add the extension function in `TensorTransformDsl.kt` so users can chain it.
3. Add the entry to this reference file.
4. Cite real call sites in tests under `skainet-data/skainet-data-transform/src/commonTest/`.
