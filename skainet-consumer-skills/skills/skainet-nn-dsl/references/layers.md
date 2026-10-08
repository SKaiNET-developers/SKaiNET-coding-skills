# Sequential layer reference

Authoritative source: `SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/nn/dsl/NetworkBuilder.kt`. Update when signatures drift.

## Entry points

```kotlin
public inline fun <reified T : DType, V> sequential(
    content: NeuralNetworkDsl<T, V>.() -> Unit
): Module<T, V>
// from: NetworkBuilder.kt:63-68

public inline fun <reified T : DType, V> sequential(
    executionContext: ExecutionContext,
    content: NeuralNetworkDsl<T, V>.() -> Unit
): Module<T, V>
// from: NetworkBuilder.kt:73-79
```

The two-arg overload wires the execution context (and via it the tensor factory + ops) at construction time. The single-arg overload uses `DefaultNeuralNetworkExecutionContext()`.

## Inputs

```kotlin
fun input(inputSize: Int, id: String = "", requiresGrad: Boolean = false)
fun input(inputShape: IntArray, id: String = "", requiresGrad: Boolean = false)  // per-sample shape, batch excluded
// from: NetworkBuilder.kt:113-129
```

Use `IntArray` form when downstream layers are spatial (`conv2d`, `maxPool2d`) and a later `flatten()` needs to know the unrolled feature count.

## Dense / Linear

```kotlin
fun dense(outputDimension: Int, id: String = "", content: DENSE<T, V>.() -> Unit = {})
fun dense(id: String = "", content: DENSE<T, V>.() -> Unit = {})

fun <TLayer : DType> dense(outputDimension: Int, id: String = "", content: DENSE<TLayer, V>.() -> Unit = {}): Module<T, V>
fun <TLayer : DType> dense(id: String = "", content: DENSE<TLayer, V>.() -> Unit = {}): Module<T, V>
// from: NetworkBuilder.kt:147-199
```

The `<TLayer>` overload allows mixed precision — one dense layer at FP16 inside an FP32 network, etc.

## Recurrent

```kotlin
fun gru(hiddenSize: Int, id: String = "", content: GRU<T, V>.() -> Unit = {})
// from: NetworkBuilder.kt:166
```

The GRU layer infers its input size from the preceding layer's output dimension. The `GRU<T, V>` scope exposes only `trainable` (`NetworkBuilder.kt:614-616`).

## Reshape / Flatten

```kotlin
fun flatten(id: String = "", content: FLATTEN<T, V>.() -> Unit = {})
// from: NetworkBuilder.kt:138
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
// from: NetworkBuilder.kt:368-378 (no block-only overload)

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
// from: NetworkBuilder.kt:276-308

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
// from: NetworkBuilder.kt:393-403 (no block-only overload)
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
// from: NetworkBuilder.kt:311-337

fun avgPool2d(
    kernelSize: Pair<Int, Int>,
    stride: Pair<Int, Int> = kernelSize,
    padding: Pair<Int, Int> = 0 to 0,
    countIncludePad: Boolean = true,
    id: String = ""
)
// from: NetworkBuilder.kt:414-420 (no block-only overload)
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
// from: NetworkBuilder.kt:340-355; UpsampleMode is `Nearest` or `Bilinear` (sk.ainet.lang.tensor.ops.UpsampleMode)
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
// from: NetworkBuilder.kt:221-263
```

## Activations

```kotlin
fun activation(id: String = "", activation: (Tensor<T, V>) -> Tensor<T, V>)
fun softmax(dim: Int = -1, id: String = "")
// from: NetworkBuilder.kt:201-209
```

`activation { it.relu() }`, `activation { it.gelu() }`, `activation { it.sigmoid() }`, `activation { it.silu() }` are the typical forms (extensions in `sk.ainet.lang.tensor.TensorExtensions.kt`); you can also call any `Tensor<T, V>` extension you've defined.

## Grouping — nested `sequential`, `stage`

```kotlin
fun sequential(content: NeuralNetworkDsl<T, V>.() -> Unit)                      // organizational grouping
fun stage(id: String, content: NeuralNetworkDsl<T, V>.() -> Unit)               // named stage/block
fun <TStage : DType> stage(id: String, content: NeuralNetworkDsl<TStage, V>.() -> Unit): Module<T, V>
// from: NetworkBuilder.kt:430-466
```

The `<TStage>` overload scopes a different precision to every layer inside the stage (mixed-precision blocks); the returned module handles the conversion.

## Not in this DSL: LLM / transformer layers

`embedding`, `rmsNorm`, `multiHeadAttention`, `swiGluFFN`, `residual` and `xielu` moved to the SKaiNET-transformers repository's llm-core module (`NetworkBuilder.kt:422-423`). The fused `scaledDotProductAttention` op (with native grouped-query attention) remains in the engine on `TensorOps` (`TensorOps.kt:389-397`).

## Layer scope blocks (`DENSE`, `CONV2D`, `MAXPOOL2D`, …)

Layer-scope content blocks expose configuration setters and weight initialisers (`NetworkBuilder.kt:460-596`). The exact members vary by layer; common ones:

- `inChannels = ...` / `outChannels = ...` (CONV*)
- `kernelSize(5)` (Int helper, sets all dims to 5) — CONV2D/CONV3D/MAXPOOL2D/AVGPOOL2D
- `stride(2)` / `padding(0)` (same Int helpers)
- `trainable = ...` (DENSE, CONV*, GRU)
- `weights { shape -> ... }` and `bias { shape -> ... }` for custom initialisation (any layer implementing `WandBTensorValueContext` — DENSE, CONV1D/2D/3D); the blocks run in `WeightsScope`/`BiasScope`, which extend the data DSL's `TensorCreationScope` (so `randn`, `uniform`, `zeros`, … work)
- DENSE additionally has `activation = ...` and `units = ...`; FLATTEN has `startDim` / `endDim`

Look at the interface declarations in `NetworkBuilder.kt` for the full member list per layer.
