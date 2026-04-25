---
name: skainet-inference
description: Use when running a SKaiNET model end-to-end — picking the right `ExecutionContext`, calling `model.forward(x, ctx)`, batching inputs, configuring the eval/train phase, applying TurboQuant for KV-cache compression. Trigger tokens include `DirectCpuExecutionContext.create()`, `DefaultNeuralNetworkExecutionContext`, `model.forward(`, `module.forward(`, `Phase.EVAL`, `Phase.TRAIN`, `ctx.inTraining`, `TurboQuantPolar`, `TurboQuantConfig`, `TurboQuantCodec`. Do NOT fire on tensor construction (`skainet-data-dsl`), model architecture definition (`skainet-nn-dsl`), or model file loading (`skainet-model-loading`).
version: 0.1.0
---

# skainet-inference

Running a SKaiNET model: `ExecutionContext` lifecycle, the forward pass, eval/train phase toggling, and TurboQuant for KV-cache or weight compression. The four steps that connect "I have a model" to "I have predictions."

## When to use

- Running a forward pass.
- Picking between `DirectCpuExecutionContext.create()` and `DefaultNeuralNetworkExecutionContext()`.
- Switching a model between eval and train phases.
- Configuring TurboQuant on tensors (KV cache, weights).
- Batching multiple inputs through one `forward` call.
- Threading concerns: which thread should host the forward pass?

## When NOT to use

- The dependency is missing (`Unresolved reference: DirectCpuExecutionContext`) — that's `skainet-consumer-setup`.
- Building tensors to feed into `forward` — that's `skainet-data-dsl`.
- Defining the model architecture — that's `skainet-nn-dsl`.
- Loading pre-trained weights — that's `skainet-model-loading`.
- Wrapping the forward pass in an Android `ViewModel` / `LifecycleScope` — coordinate with `skainet-android-integration`.

## Hard rules

1. **One `ExecutionContext` per inference session.** It owns the tensor data factory, execution stats, and (optionally) forward hooks. Don't re-create it per `forward(...)` call — it's heavyweight; reuse across calls.
2. **`Phase.EVAL` is the default for inference.** `DirectCpuExecutionContext.create()` returns `EVAL`; do not pass `Phase.TRAIN` "for safety" — dropout / batchnorm change behaviour.
3. **`forward(x, ctx)` is synchronous and CPU-bound.** Run it on a worker thread / dispatcher (`Dispatchers.Default` for compute, `Dispatchers.IO` for IO-mixed). Never on the Android main thread.
4. **Inputs MUST have the shape the model declares.** A model with `input(28 * 28)` accepts `[batch, 784]`; with `input(intArrayOf(1, 28, 28))` accepts `[batch, 1, 28, 28]`. Reshape at the source, not by silently letting the framework error in the middle of a layer.
5. **TurboQuant is opt-in.** Apply it only to specific tensors (KV cache, weights) — don't blanket-encode everything. The quantisation rounds and the choice of bits (2/3/4/8) is a quality/size trade-off the consumer must make consciously.
6. **Don't read intermediate activations through reflection.** Use `ForwardHooks` (passed via `_hooks` to the `ExecutionContext` constructor) when you need to observe layer outputs.

## Workflow

1. Create the context: `val ctx = DirectCpuExecutionContext.create()` — hold for the lifetime of the inference session.
2. Build (or load weights into) the model: a `Module<T, V>` from `sequential` / `dag`, or weights bound via a loader.
3. Build the input tensor: shape MUST match the model's declared `input(...)`.
4. Wrap the forward pass in the right coroutine context: `withContext(Dispatchers.Default) { model.forward(x, ctx) }`.
5. Process the output `Tensor<T, V>` — use the data DSL helpers, or convert to a primitive array for downstream code.

## Canonical examples

**Minimal inference loop:**

```kotlin
import sk.ainet.context.DirectCpuExecutionContext
import sk.ainet.lang.nn.dsl.sequential
import sk.ainet.lang.tensor.dsl.tensor
import sk.ainet.lang.tensor.relu
import sk.ainet.lang.types.FP32

val ctx = DirectCpuExecutionContext.create()    // Phase.EVAL by default
val model = sequential<FP32, Float> {
    input(28 * 28)
    dense(128)
    activation { it.relu() }
    dense(10)
}

val x = tensor<FP32, Float>(ctx, FP32::class) {
    tensor { shape(1, 28 * 28) { full(0.5f) } }
}

val y = model.forward(x, ctx)
// y.shape == Shape(1, 10)
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonTest/kotlin/sk/ainet/readme/ReadmeSnippetsTest.kt:36-56
```

**Real-world consumer pattern (image-in / tensor-out, with progress):**

```kotlin
val ctx: ExecutionContext = modelInstance.executionContext     // DirectCpuExecutionContext.create()
val module = modelInstance.model.create(ctx)
val inputTensor = imageLoader.imageToTensor(image, ctx)

val outputTensor = modelInstance.model.calculate(
    module = module,
    inputValue = inputTensor,
    executionContext = ctx
) { current, total, message ->
    println("Progress: $current/$total - $message")
}
// from: SKaiNET/skainet-apps/skainet-grayscale-cli/src/main/kotlin/sk/ainet/apps/grayscale/TensorConversionPipeline.kt
```

The grayscale CLI is the canonical end-to-end example: image → tensor → forward → tensor → image.

**Phase toggle (consumer rarely needs this; included for completeness):**

```kotlin
import sk.ainet.context.Phase

val inferCtx = DirectCpuExecutionContext.create(phase = Phase.EVAL)
val trainCtx = DirectCpuExecutionContext.create(phase = Phase.TRAIN)

if (ctx.inTraining) {
    // dropout active, batchnorm tracking running stats, etc.
}
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/context/Phase.kt
```

**Batched inference — pass a leading batch dim:**

```kotlin
val batch = tensor<FP32, Float>(ctx, FP32::class) {
    tensor { shape(32, 28 * 28) { fromArray(myBatchOf32Flattened) } }
}
val logits = model.forward(batch, ctx)
// logits.shape == Shape(32, 10)
```

There is no separate "batched forward" API — batching is just a leading shape dimension. This holds for `dense`, `conv2d`, `softmax(dim = -1)` (per-sample), etc.

**Threading from a Kotlin coroutine:**

```kotlin
suspend fun classify(image: Tensor<FP32, Float>, model: Module<FP32, Float>, ctx: ExecutionContext): Tensor<FP32, Float> =
    withContext(Dispatchers.Default) {
        model.forward(image, ctx)
    }
```

`Dispatchers.Default` is the right pool for CPU-bound work; `Dispatchers.IO` is sized for IO-blocking calls. Do NOT call `forward` from `Dispatchers.Main` (Android UI / UI-thread executors).

**TurboQuant for a KV cache:**

```kotlin
import sk.ainet.lang.tensor.encoding.TensorEncoding

val keyEncoding = TensorEncoding.TurboQuantPolar(bitsPerElement = 4, blockSize = 128)
val valueEncoding = TensorEncoding.TurboQuantPolar(bitsPerElement = 4, blockSize = 128)
// Plug encodings into your KV-cache implementation.
```

```kotlin
import sk.ainet.lang.tensor.ops.turboquant.TurboQuantCodec
import sk.ainet.lang.tensor.ops.turboquant.TurboQuantConfig

val config = TurboQuantConfig.polarPlusQjl(bits = 4, residualBits = 1, seed = 42)
val encoded = TurboQuantCodec.encode(rawFloats, config)
val decoded = TurboQuantCodec.decode(encoded)
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/ops/turboquant/TurboQuantCodec.kt
```

4 bits is the sweet spot for KV cache (≈8× compression, small quality hit). 8 bits is near-lossless. 2-3 bits is aggressive — use only for measured workloads.

## Related skills

- Build the input tensor — [`../skainet-data-dsl/SKILL.md`](../skainet-data-dsl/SKILL.md).
- Define the model — [`../skainet-nn-dsl/SKILL.md`](../skainet-nn-dsl/SKILL.md).
- Load pre-trained weights — [`../skainet-model-loading/SKILL.md`](../skainet-model-loading/SKILL.md).
- Threading on Android (lifecycle, scopes, memory) — [`../skainet-android-integration/SKILL.md`](../skainet-android-integration/SKILL.md).
- Java consumer running inference via `SKaiNET.context()` — [`../skainet-java-consumer/SKILL.md`](../skainet-java-consumer/SKILL.md).

## Anti-patterns

```kotlin
// WRONG — new context per call
fun classify(x: Tensor<FP32, Float>): Tensor<FP32, Float> {
    val ctx = DirectCpuExecutionContext.create()  // expensive, allocates factories
    return model.forward(x, ctx)
}
```
```kotlin
// RIGHT — context outlives the calls
class Classifier(private val model: Module<FP32, Float>) {
    private val ctx = DirectCpuExecutionContext.create()
    fun classify(x: Tensor<FP32, Float>): Tensor<FP32, Float> = model.forward(x, ctx)
}
```

```kotlin
// WRONG — forward on the Android main thread
override fun onClick(view: View) {
    val out = model.forward(input, ctx)   // blocks UI for hundreds of ms
}
```
```kotlin
// RIGHT — dispatcher
override fun onClick(view: View) {
    lifecycleScope.launch {
        val out = withContext(Dispatchers.Default) { model.forward(input, ctx) }
        renderResult(out)
    }
}
```

```kotlin
// WRONG — passing a TRAIN context for an inference workload
val ctx = DirectCpuExecutionContext.create(phase = Phase.TRAIN)
val pred = model.forward(input, ctx)   // dropout active → non-deterministic predictions
```
```kotlin
// RIGHT — EVAL for inference
val ctx = DirectCpuExecutionContext.create()   // EVAL is default
```

```kotlin
// WRONG — looping per-sample for "batching"
val outs = inputs.map { x -> model.forward(x.unsqueeze(0), ctx) }
```
```kotlin
// RIGHT — leading batch dim
val batched = stackInputs(inputs)              // Tensor with leading dim N
val outs = model.forward(batched, ctx)         // single forward call
```

## References

- [`references/execution-context.md`](references/execution-context.md) — `ExecutionContext` factories, `Phase`, hooks, stats, and the lifetime contract.
- [`references/forward-pass.md`](references/forward-pass.md) — `Module.forward(x, ctx)`, batching, output shape rules, when to convert to primitive arrays.
- [`references/turboquant.md`](references/turboquant.md) — `TurboQuantPolar`, `TurboQuantPolarQjl`, `TurboQuantConfig`, `TurboQuantCodec` with the bit/quality trade-off.
