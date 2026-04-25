# Sequential layer reference

Authoritative source: `SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/nn/dsl/NetworkBuilder.kt`. Update when signatures drift.

## Entry points

```kotlin
public inline fun <reified T : DType, V> sequential(
    content: NeuralNetworkDsl<T, V>.() -> Unit
): Module<T, V>
// from: NetworkBuilder.kt:62-67

public inline fun <reified T : DType, V> sequential(
    executionContext: ExecutionContext,
    content: NeuralNetworkDsl<T, V>.() -> Unit
): Module<T, V>
// from: NetworkBuilder.kt:72-78
```

The two-arg overload wires the execution context (and via it the tensor factory + ops) at construction time. The single-arg overload uses `DefaultNeuralNetworkExecutionContext()`.

## Inputs

```kotlin
fun input(inputSize: Int, id: String = "", requiresGrad: Boolean = false)
fun input(inputShape: IntArray, id: String = "", requiresGrad: Boolean = false)  // per-sample shape, batch excluded
// from: NetworkBuilder.kt:112-128
```

Use `IntArray` form when downstream layers are spatial (`conv2d`, `maxPool2d`) and a later `flatten()` needs to know the unrolled feature count.

## Dense / Linear

```kotlin
fun dense(outputDimension: Int, id: String = "", content: DENSE<T, V>.() -> Unit = {})
fun dense(id: String = "", content: DENSE<T, V>.() -> Unit = {})

fun <TLayer : DType> dense(outputDimension: Int, id: String = "", content: DENSE<TLayer, V>.() -> Unit = {}): Module<T, V>
fun <TLayer : DType> dense(id: String = "", content: DENSE<TLayer, V>.() -> Unit = {}): Module<T, V>
// from: NetworkBuilder.kt:146-181
```

The `<TLayer>` overload allows mixed precision — one dense layer at FP16 inside an FP32 network, etc.

## Reshape / Flatten

```kotlin
fun flatten(id: String = "", content: FLATTEN<T, V>.() -> Unit = {})
// from: NetworkBuilder.kt:137
```

## Convolutions

```kotlin
fun conv1d(
    outChannels: Int,
    kernelSize: Int,
    stride: Int = 1,
    padding: Int = 0,
    dilation: Int = 1,
    groups: Int = 1,
    bias: Boolean = true,
    id: String = "",
    content: CONV1D<T, V>.() -> Unit = {}
)
// from: NetworkBuilder.kt:356-366

fun conv2d(
    outChannels: Int,
    kernelSize: Pair<Int, Int>,
    stride: Pair<Int, Int> = 1 to 1,
    padding: Pair<Int, Int> = 0 to 0,
    dilation: Pair<Int, Int> = 1 to 1,
    groups: Int = 1,
    bias: Boolean = true,
    id: String = "",
    content: CONV2D<T, V>.() -> Unit = {}
)
fun conv2d(id: String = "", content: CONV2D<T, V>.() -> Unit)  // block-only form
// from: NetworkBuilder.kt:264-289

fun conv3d(
    outChannels: Int,
    kernelSize: Triple<Int, Int, Int>,
    stride: Triple<Int, Int, Int> = Triple(1, 1, 1),
    padding: Triple<Int, Int, Int> = Triple(0, 0, 0),
    dilation: Triple<Int, Int, Int> = Triple(1, 1, 1),
    groups: Int = 1,
    bias: Boolean = true,
    id: String = "",
    content: CONV3D<T, V>.() -> Unit = {}
)
// from: NetworkBuilder.kt:381-391
```

## Pooling

```kotlin
fun maxPool2d(
    kernelSize: Pair<Int, Int>,
    stride: Pair<Int, Int> = kernelSize,
    padding: Pair<Int, Int> = 0 to 0,
    id: String = ""
)
fun maxPool2d(id: String = "", content: MAXPOOL2D<T, V>.() -> Unit)  // block-only form
// from: NetworkBuilder.kt:299-318

fun avgPool2d(
    kernelSize: Pair<Int, Int>,
    stride: Pair<Int, Int> = kernelSize,
    padding: Pair<Int, Int> = 0 to 0,
    countIncludePad: Boolean = true,
    id: String = ""
)
// signature continues from NetworkBuilder.kt:393+; check source for full args
```

## Upsampling

```kotlin
fun upsample2d(
    scale: Pair<Int, Int> = 2 to 2,
    mode: UpsampleMode = UpsampleMode.Nearest,
    alignCorners: Boolean = false,
    id: String = ""
)
fun upsample2d(id: String = "", content: UPSAMPLE2D<T, V>.() -> Unit)
// from: NetworkBuilder.kt:328-341
```

## Normalization

```kotlin
fun batchNorm(
    numFeatures: Int,
    eps: Double = 1e-5,
    momentum: Double = 0.1,
    affine: Boolean = true,
    id: String = ""
)
fun groupNorm(
    numGroups: Int,
    numChannels: Int,
    eps: Double = 1e-5,
    affine: Boolean = true,
    id: String = ""
)
fun layerNorm(
    normalizedShape: IntArray,
    eps: Double = 1e-5,
    elementwiseAffine: Boolean = true,
    id: String = ""
)
// from: NetworkBuilder.kt:209-249
```

## Activations

```kotlin
fun activation(id: String = "", activation: (Tensor<T, V>) -> Tensor<T, V>)
fun softmax(dim: Int = -1, id: String = "")
// from: NetworkBuilder.kt:189-197
```

`activation { it.relu() }`, `activation { it.gelu() }`, `activation { it.sigmoid() }`, `activation { it.silu() }` are the typical forms; you can also call any `Tensor<T, V>` extension you've defined.

## Layer scope blocks (`DENSE`, `CONV2D`, `MAXPOOL2D`, …)

Layer-scope content blocks expose configuration setters and weight initialisers. The exact members vary by layer; common ones:

- `inChannels = ...` (CONV*)
- `outChannels = ...` (CONV*, when using block-only form)
- `kernelSize(5)` (sets all dims to 5)
- `stride(2)` / `padding(0)`
- `weights { shape -> ... }` and `bias { shape -> ... }` for custom initialisation

Look at the layer's source file in `sk.ainet.lang.nn` for the full member list.
