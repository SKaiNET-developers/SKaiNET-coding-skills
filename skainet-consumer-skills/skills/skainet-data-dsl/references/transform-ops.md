# Transform pipeline operations

Authoritative source: `SKaiNET/skainet-data/skainet-data-transform/src/commonMain/kotlin/sk/ainet/data/transform/TensorTransformDsl.kt` (extension functions on `Transform<I, Tensor<T, V>>`). Update when extensions drift.

## Pattern

A pipeline is a chain of `Transform<In, Out>` values composed by `then`. The DSL exposes one extension per transform; each takes the `ExecutionContext` so the produced tensors live on the right backend.

```kotlin
val preprocess = pipeline<Tensor<FP32, Float>>()
    .rescale(ctx, scale = 255f)
    .normalize(ctx, mean = mean, std = std, channelAxis = -1)
    .unsqueeze(ctx, 0)

val batch = preprocess(raw)
// pipeline(): SKaiNET/skainet-data/skainet-data-transform/src/commonMain/kotlin/sk/ainet/data/transform/Transform.kt:168
```

`pipeline<T>()` returns an `Identity<T>` transform to chain from; `then` is the infix composer on `Transform<I, O>` (`Transform.kt:92`).

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
// Channel-wise `(output - mean) / std` along `channelAxis`. Default channelAxis = -1 (last).
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

public fun <I, T : DType, V> Transform<I, Tensor<T, V>>.reshape(
    ctx: ExecutionContext,
    shape: Shape
): Transform<I, Tensor<T, V>>
public fun <I, T : DType, V> Transform<I, Tensor<T, V>>.reshape(
    ctx: ExecutionContext,
    vararg dims: Int
): Transform<I, Tensor<T, V>>
// from: TensorTransformDsl.kt:84-102

public fun <I, T : DType, V> Transform<I, Tensor<T, V>>.flatten(
    ctx: ExecutionContext,
    startDim: Int = 0,
    endDim: Int = -1
): Transform<I, Tensor<T, V>>
// from: TensorTransformDsl.kt:107-112

public fun <I, T : DType, V> Transform<I, Tensor<T, V>>.unsqueeze(
    ctx: ExecutionContext,
    dim: Int
): Transform<I, Tensor<T, V>>
// Adds a size-1 dimension at `dim`. NOTE: takes the ExecutionContext like every other extension.
// from: TensorTransformDsl.kt:119-123

public fun <I, T : DType, V> Transform<I, Tensor<T, V>>.squeeze(
    ctx: ExecutionContext,
    dim: Int? = null
): Transform<I, Tensor<T, V>>
// Removes the size-1 dimension at `dim`, or all size-1 dimensions when null.
// from: TensorTransformDsl.kt:130-134
```

That is the complete extension list as of 0.57.0.

## Normalization presets

`TensorTransformDsl.kt:150-178` ships three preset objects, each with `mean` and `std` FloatArrays (RGB order):

```kotlin
pipeline.normalize(ctx, ImageNet.mean, ImageNet.std)      // 0.485/0.456/0.406, 0.229/0.224/0.225
pipeline.normalize(ctx, CIFAR10Norm.mean, CIFAR10Norm.std)
pipeline.normalize(ctx, MNISTNorm.mean, MNISTNorm.std)    // grayscale, single channel
```

## Context-scoped form — `transforms(ctx) { ... }`

`TransformScope<T, V>` re-declares every extension above without the `ctx` parameter; `transforms(ctx) { ... }` opens the scope (`TensorTransformDsl.kt:197-287`):

```kotlin
val preprocessing = transforms(ctx) {
    pipeline<Tensor<FP32, Float>>()
        .rescale(255f)
        .normalize(ImageNet.mean, ImageNet.std)
        .unsqueeze(0)
}
```

## Where the actual transform classes live

The functions above produce instances of `Normalize`, `Rescale`, `ScaleAndShift`, `Clamp`, `Reshape`, `Flatten`, `Unsqueeze`, `Squeeze` — concrete classes in `TensorTransforms.kt` in the same package. The DSL extensions are the call site; the classes are the implementation.

## When to NOT use a pipeline

- Single transform → just call the underlying op directly (`tensor.ops.divScalar(tensor, 255f)`).
- Variable-shape data per call (e.g. ragged batches) → the pipeline expects a single static input shape; use a custom function.

## Adding a new transform

1. Define a `class NewTransform(ctx: ExecutionContext, ...)` implementing `Transform<Tensor<T, V>, Tensor<T, V>>`.
2. Add the extension function in `TensorTransformDsl.kt` so users can chain it.
3. Add the entry to this reference file.
4. Cite real call sites in tests under `skainet-data/skainet-data-transform/src/commonTest/`.
