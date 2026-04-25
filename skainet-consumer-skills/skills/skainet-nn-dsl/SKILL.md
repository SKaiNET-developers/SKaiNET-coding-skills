---
name: skainet-nn-dsl
description: Use when defining a neural network architecture with the SKaiNET public DSL — `sequential<T, V> { ... }` for linear stacks, `dag { ... }` for graphs with branching / skip connections. Applies in both consumer apps and inside the SKaiNET repo. Trigger tokens include `sequential<`, `dag {`, `dagModule`, layer names (`input`, `dense`, `flatten`, `activation`, `softmax`, `batchNorm`, `groupNorm`, `layerNorm`, `conv1d`, `conv2d`, `conv3d`, `maxPool2d`, `avgPool2d`, `upsample2d`), DAG nodes (`parameter`, `constant`, `matmul`, `relu`, `output`). Do NOT fire on tensor *creation* (that's `skainet-data-dsl`), on assertions (use the contributor `skainet-testing` skill in-repo), or on running a model end-to-end (that's `skainet-inference`).
version: 0.1.0
---

# skainet-nn-dsl

Building blocks for neural networks: the sequential builder for layered models, the DAG builder for graphs with arbitrary wiring, and the rule for choosing between them. This skill is a cheatsheet — DSL skills teach usage rather than enforce constraints.

## When to use

- Defining a model with stacked layers (MLP, CNN, simple encoder/decoder).
- Defining a model with skip connections, multiple inputs, or multiple outputs (ResNet block, YOLO head, multi-task heads).
- Reusing a sub-graph as a `DagModule`.
- Annotating a layer block (`conv2d(...) { inChannels = ... }`).

## When NOT to use

- Building input tensors or preprocessing pipelines for the model — `skainet-data-dsl`.
- Asserting model output values in tests — `skainet-testing`.
- Exposing a model builder to Java callers — `skainet-java-interop`.
- Configuring KSP for tracing wrappers — `gradle-multimodule` + `kmp`.

## Cheatsheet

### Sequential — linear stack of layers

```kotlin
val model = sequential<FP32, Float> {
    input(28 * 28)
    dense(128)
    activation { tensor -> tensor.relu() }
    dense(10)
}
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonTest/kotlin/sk/ainet/readme/ReadmeSnippetsTest.kt:38-43
```

### Sequential CNN

```kotlin
val cnn = sequential<FP32, Float> {
    input(intArrayOf(1, 28, 28))                                 // C, H, W per sample
    conv2d(outChannels = 16, kernelSize = 3 to 3, stride = 1 to 1, padding = 0 to 0)
    activation { it.relu() }
    maxPool2d(kernelSize = 2 to 2, stride = 2 to 2)
    flatten()
    dense(64)
    activation { it.relu() }
    dense(10)
    softmax(dim = -1)
}
```

Layer signatures (from `NetworkBuilder.kt:104-400+`):

```kotlin
input(inputSize: Int, id: String = "", requiresGrad: Boolean = false)
input(inputShape: IntArray, id: String = "", requiresGrad: Boolean = false)
dense(outputDimension: Int, id: String = "", content: DENSE<T, V>.() -> Unit = {})
flatten(id: String = "", content: FLATTEN<T, V>.() -> Unit = {})
activation(id: String = "", activation: (Tensor<T, V>) -> Tensor<T, V>)
softmax(dim: Int = -1, id: String = "")
conv1d(outChannels: Int, kernelSize: Int, stride: Int = 1, padding: Int = 0, dilation: Int = 1, groups: Int = 1, bias: Boolean = true, id: String = "", content: CONV1D<T, V>.() -> Unit = {})
conv2d(outChannels: Int, kernelSize: Pair<Int, Int>, stride: Pair<Int, Int> = 1 to 1, padding: Pair<Int, Int> = 0 to 0, dilation: Pair<Int, Int> = 1 to 1, groups: Int = 1, bias: Boolean = true, id: String = "", content: CONV2D<T, V>.() -> Unit = {})
conv3d(outChannels: Int, kernelSize: Triple<Int, Int, Int>, ...)
maxPool2d(kernelSize: Pair<Int, Int>, stride: Pair<Int, Int> = kernelSize, padding: Pair<Int, Int> = 0 to 0, id: String = "")
avgPool2d(kernelSize: Pair<Int, Int>, ...)
upsample2d(scale: Pair<Int, Int> = 2 to 2, mode: UpsampleMode = UpsampleMode.Nearest, alignCorners: Boolean = false, id: String = "")
batchNorm(numFeatures: Int, eps: Double = 1e-5, momentum: Double = 0.1, affine: Boolean = true, id: String = "")
groupNorm(numGroups: Int, numChannels: Int, eps: Double = 1e-5, affine: Boolean = true, id: String = "")
layerNorm(normalizedShape: IntArray, eps: Double = 1e-5, elementwiseAffine: Boolean = true, id: String = "")
```

Each spatial layer has a "content-block-only" overload (`conv2d(id) { outChannels = ...; kernelSize(5); stride(1); padding(2) }`). Use it when configuration is verbose enough to warrant block syntax.

### Activation as a separate layer vs function

```kotlin
// As a layer with id (preferred when traceability matters)
activation(id = "post_dense_1") { it.relu() }

// As an activation function inline (not a separate layer in the topology)
val out = ctx.relu(dense_out)  // operator on a Tensor
```

### DAG — arbitrary wiring

```kotlin
val program = dag {
    val x = input<FP32>("x", TensorSpec("x", listOf(1, 4), "FP32"))
    val w = parameter<FP32, Float>("w") { shape(4, 4) { ones() } }
    val mm = matmul(x, w)
    val y = relu(mm)
    output(y)
}
// from: SKaiNET/skainet-lang/skainet-lang-dag/src/commonMain/kotlin/sk/ainet/lang/dag/GraphDsl.kt:48-65
```

DAG node helpers (from `GraphDsl.kt`):

```kotlin
input<T : DType>(name: String, spec: TensorSpec = TensorSpec(name, null, "unknown")): GraphValue<T>
parameter<T : DType>(name: String, spec: TensorSpec): GraphValue<T>
parameter<reified T : DType, V>(name: String, builder: SymbolicTensorBuilder<T>.() -> TensorSpec): GraphValue<T>
constant<T : DType>(name: String, spec: TensorSpec): GraphValue<T>
constant<reified T : DType, V>(name: String, builder: SymbolicTensorBuilder<T>.() -> TensorSpec): GraphValue<T>
op(operation: Operation, inputs: List<GraphValue<*>>, id: String = "", attributes: Map<String, Any?>): List<GraphValue<*>>
output(vararg values: GraphValue<*>)
```

The DAG builder is **definition-only** — no tensors are allocated. The returned `GraphProgram` is consumed by `skainet-compile-dag` to produce a `ComputeGraph`.

### Reusable sub-graphs — `dagModule`

```kotlin
val residualBlock = dagModule { inputs ->
    val x = inputs[0]
    val w1 = parameter<FP32, Float>("w1") { shape(64, 64) { randn(0f, 0.02f) } }
    val w2 = parameter<FP32, Float>("w2") { shape(64, 64) { randn(0f, 0.02f) } }
    val h = relu(matmul(x, w1))
    val y = matmul(h, w2)
    listOf(/* residual add */ add(x, y))
}

val program = dag {
    val x = input<FP32>("x", TensorSpec("x", listOf(1, 64), "FP32"))
    val out = module(residualBlock, listOf(x))
    output(out[0])
}
// from: SKaiNET/skainet-lang/skainet-lang-dag/src/commonMain/kotlin/sk/ainet/lang/dag/GraphDsl.kt:222-257
```

## Decision rule — sequential or DAG?

| Architecture | Builder |
|---|---|
| MLP, CNN with linear stack of layers, simple RNN | `sequential<T, V> { }` |
| ResNet (skip connections), U-Net, multi-input, multi-output | `dag { }` |
| You need symbolic compilation to C / HLO / ONNX | `dag { }` (compiler operates on `GraphProgram`) |
| You're in a unit test and want `model.forward(x, ctx)` directly | `sequential` |
| You'd like to reuse a sub-graph in multiple places | `dag` + `dagModule { }` |

`sequential` produces a `Module<T, V>` you can call `forward(x, ctx)` on. `dag` produces a `GraphProgram` for downstream compilation.

## Workflow

1. Pick the builder via the table above.
2. Choose `<T, V>` from the dtype/value-type table (`FP32` ↔ `Float`, `Int8` ↔ `Byte`, …).
3. For sequential: declare `input(...)` first; chain layers; finish with the prediction layer (often `dense(numClasses)` followed by `softmax(dim = -1)`).
4. For DAG: declare every `input` and `parameter` upfront, build intermediate values, mark outputs with `output(...)`.
5. Run a forward pass in a test using `skainet-testing` patterns to verify shapes and tolerances.

## Related skills

- The input tensor for `forward(x, ctx)` and parameter tensors used in `parameter { shape(…) { … } }` come from the data DSL — see [`../skainet-data-dsl/SKILL.md`](../skainet-data-dsl/SKILL.md).
- Loading pre-trained weights into a `parameter`-style graph — see [`../skainet-model-loading/SKILL.md`](../skainet-model-loading/SKILL.md).
- Running the forward pass: `ExecutionContext`, batching, threading — see [`../skainet-inference/SKILL.md`](../skainet-inference/SKILL.md).
- Calling a network from Java — see [`../skainet-java-consumer/SKILL.md`](../skainet-java-consumer/SKILL.md).
- (In-repo only) Asserting forward-pass output values in tests — see the contributor `skainet-testing` skill.

## Anti-patterns

```kotlin
// WRONG — calling relu() as a layer (no such layer; relu is an activation function)
sequential<FP32, Float> {
    input(28 * 28)
    dense(128)
    relu()              // does not exist on NeuralNetworkDsl
}
```
```kotlin
// RIGHT — wrap with `activation { ... }` or call .relu() inline on a tensor
sequential<FP32, Float> {
    input(28 * 28)
    dense(128)
    activation { it.relu() }
}
```

```kotlin
// WRONG — using sequential for a residual block
sequential<FP32, Float> {
    input(intArrayOf(64))
    dense(64)
    activation { it.relu() }
    // ... how do I add the input back to this output? sequential cannot.
}
```
```kotlin
// RIGHT — DAG for skip connections
dag {
    val x = input<FP32>("x", TensorSpec("x", listOf(1, 64), "FP32"))
    val w = parameter<FP32, Float>("w") { shape(64, 64) { randn(0f, 0.02f) } }
    val h = relu(matmul(x, w))
    val y = add(x, h)              // residual
    output(y)
}
```

```kotlin
// WRONG — placing the input declaration after a layer
sequential<FP32, Float> {
    dense(128)         // there is no inferred input shape yet
    input(28 * 28)
}
```
```kotlin
// RIGHT — input first
sequential<FP32, Float> {
    input(28 * 28)
    dense(128)
}
```

## References

- [`references/layers.md`](references/layers.md) — every public layer signature on `NeuralNetworkDsl<T, V>`, with full default values.
- [`references/dag-nodes.md`](references/dag-nodes.md) — every public method on `DagBuilder`, with shape-inference notes.
- [`references/sequential-vs-dag.md`](references/sequential-vs-dag.md) — extended decision tree, including the cases where you start with sequential and migrate to DAG mid-development.
