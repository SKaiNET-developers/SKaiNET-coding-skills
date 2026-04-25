---
name: skainet-model-loading
description: Use when loading a pre-trained model into a SKaiNET-based app — GGUF (`GGUFModelReader`), ONNX (`OnnxLoader`), SafeTensors (`SafeTensorsParametersLoader`), or JSON. Trigger tokens include `GGUFModelReader`, `OnnxLoader.fromModelSource`, `SafeTensorsParametersLoader`, `loadGGUF`, `loadOnnx`, `.safetensors`, `.gguf`, `.onnx`, `ParametersLoader`. Do NOT fire on `model.forward(x, ctx)` (that's `skainet-inference`), defining model architecture in code (`skainet-nn-dsl`), or constructing tensors from raw arrays (`skainet-data-dsl`).
version: 0.1.0
---

# skainet-model-loading

Loading pre-trained models in the four formats SKaiNET supports: GGUF (LLM weights, llama.cpp ecosystem), ONNX (cross-framework graph + weights), SafeTensors (HuggingFace weights), and the project's own JSON serialisation. Each format has a dedicated loader in `skainet-io-*`.

## When to use

- Loading a `.gguf` / `.onnx` / `.safetensors` / `.json` file from disk, classpath, or assets.
- Picking which format to use for a new model file.
- Streaming weights into a `Module` built with `sequential` or `dag`.
- Reading the metadata / tokenizer config out of a GGUF file.

## When NOT to use

- The dependency is missing (`Unresolved reference: GGUFModelReader`) — that's `skainet-consumer-setup`.
- The model is defined inline with the DSL and weights are random / hand-set — that's `skainet-nn-dsl` + `skainet-data-dsl`.
- The forward pass after loading — that's `skainet-inference`.
- Loading from Android `AssetManager` specifically — coordinate with `skainet-android-integration`.

## Hard rules

1. **One format = one loader artifact.** Don't add `skainet-io-onnx` if the consumer is only loading `.gguf` files; it brings pbandk and the protobuf runtime. Use the artifact picker in `skainet-consumer-setup`.
2. **Loaders are coroutine-suspending. Call them from a coroutine.** `OnnxLoader.load()`, `GGUFModelReader.loadTensor(name)`, `SafeTensorsParametersLoader.load(...)` are all `suspend`. Wrap from non-coroutine code with `runBlocking { }` only at the top level (CLI / test). In an Android `ViewModel`, use `viewModelScope.launch { }`.
3. **Loaders take a source factory, not a path string.** The signature is `() -> RandomAccessSource` (or `suspend () -> Source`). Open the file inside the lambda so the loader controls lifetime; never call `.use { }` outside.
4. **The tensor produced by a loader is `Tensor<T, V>` with a known dtype (FP32 unless requested otherwise).** Pick the dtype with the loader's typed `load<T, V>(ctx, dtype, …)` overload — don't load to FP32 then `cast()` to a smaller dtype unless quantisation is intentional.
5. **Pass an `onProgress` callback** for files >50 MB — the consumer-facing wrapper expects user feedback during long loads.

## Workflow

1. Pick the format. If converting between formats, use `skainet-compile-*` (separate skill, separate concern).
2. Check the matching artifact is on the classpath (see `skainet-consumer-setup`).
3. Construct the loader with a source factory and (optional) progress callback.
4. Inside a coroutine, call `load(...)` — bind into your model's `Module` parameters or hold the `ModelReader` for streaming.
5. Test with a small known-good file before wiring into production code paths.

## Format picker

| Format | Loader | When to pick |
|---|---|---|
| GGUF | `GGUFModelReader` | LLM checkpoints from llama.cpp / ollama; tokenizer metadata embedded; quantised weights (Q4_0, Q8_0, …). |
| SafeTensors | `SafeTensorsParametersLoader` | HuggingFace models; transformer weights; safe (no pickle). |
| ONNX | `OnnxLoader<ModelProto>` | Cross-framework models (PyTorch / TensorFlow exports); graph + weights together. |
| JSON | `skainet-compile-json` | SKaiNET's own portable serialisation; for round-tripping models built with the DSL. |

## Canonical examples

**GGUF — `GGUFModelReader`:**

```kotlin
import sk.ainet.io.gguf.GGUFModelReader
import sk.ainet.context.DirectCpuExecutionContext
import kotlinx.coroutines.runBlocking

val ctx = DirectCpuExecutionContext.create()
val reader = GGUFModelReader(/* source factory pointing at file */)
runBlocking {
    val metadata = reader.metadata               // Map<String, Any>: arch, vocab, etc.
    val tensorInfos = reader.tensors             // Map<String, TensorInfo>: shape + dtype per tensor
    val qProj = reader.loadTensor("model.layers.0.self_attn.q_proj.weight")
    // bind qProj into your model's parameters
}
reader.close()
// from: SKaiNET/skainet-io/skainet-io-gguf/src/commonMain/kotlin/sk/ainet/io/gguf/GGUFModelReader.kt (public surface)
```

GGUF is streaming-friendly — `loadTensor(name)` reads one tensor at a time, suitable for large LLM weights that don't fit in memory at once.

**SafeTensors — `SafeTensorsParametersLoader`:**

```kotlin
import sk.ainet.io.safetensors.SafeTensorsParametersLoader
import sk.ainet.lang.types.FP32
import kotlinx.coroutines.runBlocking

val ctx = DirectCpuExecutionContext.create()
val loader = SafeTensorsParametersLoader(
    sourceProvider = { createRandomAccessSource("model.safetensors") },
    onProgress = { current, total, name ->
        println("[$current/$total] $name")
    }
)
runBlocking {
    loader.load(ctx, FP32::class) { name, tensor ->
        // bind 'name' -> 'tensor' into your Module's parameter map
    }
}
// from: SKaiNET/skainet-io/skainet-io-safetensors/src/commonMain/kotlin/sk/ainet/io/safetensors/SafeTensorsParametersLoader.kt (public surface)
```

SafeTensors is callback-driven — the loader hands you each tensor as it's parsed; you bind it where it belongs.

**ONNX — `OnnxLoader.fromModelSource`:**

```kotlin
import sk.ainet.io.onnx.OnnxLoader
import kotlinx.coroutines.runBlocking
import kotlinx.io.asSource

runBlocking {
    val loader = OnnxLoader.fromModelSource {
        java.io.File("model.onnx").inputStream().asSource()
    }
    val loaded = loader.load()
    val proto = loaded.proto         // ModelProto from pbandk
    val rawBytes = loaded.rawBytes   // for re-serialisation
    // walk proto.graph.nodes / proto.graph.initializers
}
// from: SKaiNET/skainet-io/skainet-io-onnx/src/commonMain/kotlin/sk/ainet/io/onnx/OnnxLoader.kt (public surface)
```

ONNX is a graph format — the loader hands you the protobuf representation. Lowering ONNX into a runnable SKaiNET `Module` is the next step (consumer apps typically use `skainet-compile-*` for that).

**Source factories — common idioms:**

```kotlin
// File on disk (JVM/desktop)
val src: () -> RandomAccessSource = { JvmFileRandomAccessSource(java.io.File("path")) }

// Classpath resource (server-side)
val src: () -> RandomAccessSource = {
    val bytes = MyClass::class.java.getResourceAsStream("/model.gguf")!!.readBytes()
    BytesRandomAccessSource(bytes)
}

// Android assets — see ../skainet-android-integration/SKILL.md
```

## Related skills

- Adding the right `skainet-io-*` artifact — [`../skainet-consumer-setup/SKILL.md`](../skainet-consumer-setup/SKILL.md).
- Running the loaded model — [`../skainet-inference/SKILL.md`](../skainet-inference/SKILL.md).
- Defining the model architecture that you're loading weights INTO — [`../skainet-nn-dsl/SKILL.md`](../skainet-nn-dsl/SKILL.md).
- Loading from Android assets — [`../skainet-android-integration/SKILL.md`](../skainet-android-integration/SKILL.md).
- Java consumer using `TokenizerFactory.fromGguf(...)` — [`../skainet-java-consumer/SKILL.md`](../skainet-java-consumer/SKILL.md).

## Anti-patterns

```kotlin
// WRONG — calling a suspend loader from non-coroutine code
val loaded = loader.load()  // compile error: 'load' is suspend
```
```kotlin
// RIGHT — wrap in a coroutine builder appropriate to the host
runBlocking { val loaded = loader.load() }              // CLI / test
viewModelScope.launch { val loaded = loader.load() }    // Android ViewModel
```

```kotlin
// WRONG — opening the file outside the loader's source factory
val source = JvmFileRandomAccessSource(File("model.safetensors"))
val loader = SafeTensorsParametersLoader(sourceProvider = { source })
// Now multiple loads share one already-opened source — no, the loader expects to control lifetime.
```
```kotlin
// RIGHT — open inside the lambda
val loader = SafeTensorsParametersLoader(
    sourceProvider = { JvmFileRandomAccessSource(File("model.safetensors")) }
)
```

```kotlin
// WRONG — load to FP32 then cast to FP16
val tensor = loader.load(...)            // FP32
val small = tensor.cast<FP16, Float>()   // wastes the FP32 alloc
```
```kotlin
// RIGHT — request FP16 directly from the typed loader overload
loader.load(ctx, FP16::class) { name, tensor -> ... }
```

```kotlin
// WRONG — silently loading a multi-GB GGUF without progress feedback
val reader = GGUFModelReader(sourceProvider)
runBlocking { val w = reader.loadTensor("...") }   // 30 second freeze
```
```kotlin
// RIGHT — use loaders that accept onProgress, surface progress to the UI / log
val loader = SafeTensorsParametersLoader(sourceProvider, onProgress = { c, t, n -> ui.update(c, t) })
```

## References

- [`references/loaders.md`](references/loaders.md) — full signature of every loader, with the suspending / non-suspending split and the entry-point factory methods.
- [`references/format-picker.md`](references/format-picker.md) — extended decision tree for "I have a model file, which format is it and which loader?".
