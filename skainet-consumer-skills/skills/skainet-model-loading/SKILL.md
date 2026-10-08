---
name: skainet-model-loading
description: Use when loading a pre-trained model into a SKaiNET-based app — GGUF (`StreamingGgufParametersLoader`), ONNX (`OnnxLoader`), SafeTensors (`SafeTensorsParametersLoader`, `ShardedSafeTensorsParametersLoader`), or JSON. Trigger tokens include `StreamingGgufParametersLoader`, `GGUFModelReader`, `OnnxLoader.fromModelSource`, `SafeTensorsParametersLoader`, `ShardedSafeTensorsParametersLoader`, `loadGGUF`, `loadOnnx`, `.safetensors`, `.gguf`, `.onnx`, `ParametersLoader`. Do NOT fire on `model.forward(x, ctx)` (that's `skainet-inference`), defining model architecture in code (`skainet-nn-dsl`), or constructing tensors from raw arrays (`skainet-data-dsl`).
version: 0.1.0
---

# skainet-model-loading

Loading pre-trained models in the four formats SKaiNET supports: GGUF (LLM weights, llama.cpp ecosystem), ONNX (cross-framework graph + weights), SafeTensors (HuggingFace weights, single-file or sharded), and the project's own JSON serialisation. Each format has a dedicated loader in `skainet-io-*`.

## When to use

- Loading a `.gguf` / `.onnx` / `.safetensors` / `.json` file from disk, classpath, or assets.
- Loading a sharded HuggingFace checkpoint (`model.safetensors.index.json` + `model-NNNNN-of-NNNNN.safetensors`).
- Picking which format to use for a new model file.
- Streaming weights into a `Module` built with `sequential` or `dag`.
- Reading the metadata / tokenizer config out of a GGUF file.

## When NOT to use

- The dependency is missing (`Unresolved reference: StreamingGgufParametersLoader`) — that's `skainet-consumer-setup`.
- The model is defined inline with the DSL and weights are random / hand-set — that's `skainet-nn-dsl` + `skainet-data-dsl`.
- The forward pass after loading — that's `skainet-inference`.
- Loading from Android `AssetManager` specifically — coordinate with `skainet-android-integration`.

## Hard rules

1. **One format = one loader artifact.** Don't add `skainet-io-onnx` if the consumer is only loading `.gguf` files; it brings pbandk and the protobuf runtime. Use the artifact picker in `skainet-consumer-setup`.
2. **Loaders are coroutine-suspending. Call them from a coroutine.** `OnnxLoader.load()`, `StreamingGgufParametersLoader.load(...)`, `SafeTensorsParametersLoader.load(...)` are all `suspend`. Wrap from non-coroutine code with `runBlocking { }` only at the top level (CLI / test). In an Android `ViewModel`, use `viewModelScope.launch { }`.
3. **Loaders take a source factory, not a path string.** The signature is `() -> RandomAccessSource` (or `suspend () -> Source` for ONNX). Open the file inside the lambda — `sk.ainet.io.openRandomAccessSource(path)` is the one cross-platform factory — so the loader controls lifetime; never call `.use { }` outside. (Exception: `ShardedSafeTensorsParametersLoader` takes the index-file *path*, because it must resolve sibling shard files itself.)
4. **Don't dequantise by accident.** The typed `load<T, V>(ctx, dtype, …)` call picks the target dtype; the GGUF streaming loader preserves quantised source types (Q4_K, Q8_0, …) as packed tensor data instead of widening them. Don't load to FP32 then `cast()` to a smaller dtype unless quantisation is intentional.
5. **Pass an `onProgress` callback** for files >50 MB — the consumer-facing wrapper expects user feedback during long loads. `current`/`total` are tensor counts; `message` is the tensor name.
6. **`GGUFModelReader` is a deprecated fail-fast stub** (since the dtype-policy rework): its `loadTensor` throws. Use `StreamingGgufParametersLoader` — the legacy facade exists only so old code keeps compiling.

## Workflow

1. Pick the format. If converting between formats, use `skainet-compile-*` (separate skill, separate concern).
2. Check the matching artifact is on the classpath (see `skainet-consumer-setup`).
3. Construct the loader with a source factory and (optional) progress callback.
4. Inside a coroutine, call `load(...)` and bind each delivered tensor into your model's `Module` parameters (the `WeightMapper` helpers in `sk.ainet.io.weights` do name-based mapping).
5. Test with a small known-good file before wiring into production code paths.

## Format picker

| Format | Loader | When to pick |
|---|---|---|
| GGUF | `StreamingGgufParametersLoader` | LLM checkpoints from llama.cpp / ollama; tokenizer metadata embedded; quantised weights (Q4_K, Q8_0, …) preserved as packed storage. |
| SafeTensors (single file) | `SafeTensorsParametersLoader` | HuggingFace models; transformer weights; safe (no pickle). |
| SafeTensors (sharded) | `ShardedSafeTensorsParametersLoader` | Multi-file HF checkpoints with `model.safetensors.index.json`. |
| ONNX | `OnnxLoader<ModelProto>` | Cross-framework models (PyTorch / TensorFlow exports); graph + weights together. |
| JSON | `skainet-compile-json` | SKaiNET's own portable serialisation; for round-tripping models built with the DSL. |

## Canonical examples

**GGUF — `StreamingGgufParametersLoader`:**

```kotlin
import sk.ainet.io.gguf.StreamingGgufParametersLoader
import sk.ainet.io.openRandomAccessSource
import sk.ainet.context.DirectCpuExecutionContext
import sk.ainet.lang.types.FP32
import kotlinx.coroutines.runBlocking

val ctx = DirectCpuExecutionContext.create()
val loader = StreamingGgufParametersLoader(
    sourceProvider = { openRandomAccessSource("model-q4.gguf")!! },
    onProgress = { current, total, name -> println("[$current/$total] $name") }
)
runBlocking {
    loader.load(ctx, FP32::class) { name, tensor ->
        // F32/I32 arrive dense; Q4_K / Q8_0 / … arrive as packed block storage
        // bind 'name' -> 'tensor' into your Module's parameters
    }
}
// from: SKaiNET/skainet-io/skainet-io-gguf/src/commonMain/kotlin/sk/ainet/io/gguf/StreamingGgufParametersLoader.kt:59-115 (public surface)
```

The streaming loader parses only the header up front and loads tensor data on demand — suitable for large LLM weights. A file containing tensors outside the supported set fails fast, before any tensor is delivered. Optional constructor knobs: `weightForm` / `weightFormFor` (encoding × byte order × shape × residency, e.g. `WeightForm(residency = WeightResidency.MAPPED)` to serve weights from memory-mapped pages), `keepF16Native` / `keepBf16Native`. For metadata/tokenizer access, use `StreamingGGUFReader.open(source).fields` (e.g. `"general.architecture"`) and `TokenizerFactory.fromGguf(fields)`.

**SafeTensors — `SafeTensorsParametersLoader`:**

```kotlin
import sk.ainet.io.safetensors.SafeTensorsParametersLoader
import sk.ainet.io.openRandomAccessSource
import sk.ainet.lang.types.FP32
import kotlinx.coroutines.runBlocking

val ctx = DirectCpuExecutionContext.create()
val loader = SafeTensorsParametersLoader(
    sourceProvider = { openRandomAccessSource("model.safetensors")!! },
    onProgress = { current, total, name ->
        println("[$current/$total] $name")
    },
    tensorFilter = { info -> !info.name.endsWith(".rotary_emb.inv_freq") }  // optional (0.54.0+)
)
runBlocking {
    loader.load(ctx, FP32::class) { name, tensor ->
        // bind 'name' -> 'tensor' into your Module's parameter map
    }
}
// from: SKaiNET/skainet-io/skainet-io-safetensors/src/commonMain/kotlin/sk/ainet/io/safetensors/SafeTensorsParametersLoader.kt:49-136 (public surface)
```

SafeTensors is callback-driven — the loader hands you each tensor as it's parsed; you bind it where it belongs. `tensorFilter` skips tensors without reading them (name allowlists, size guards, dtypes the requested target can't accept) — filtered tensors don't count toward progress. BF16/F16 tensors dequantise to FP32 by default; `bf16Policy` / `fp16Policy = NarrowFloatLoadPolicy.KEEP_NATIVE` keeps the on-disk layout.

**Sharded SafeTensors — `ShardedSafeTensorsParametersLoader` (0.53.0+):**

```kotlin
import sk.ainet.io.safetensors.ShardedSafeTensorsParametersLoader

val loader = ShardedSafeTensorsParametersLoader(
    indexPath = "/models/gemma/model.safetensors.index.json",
    onProgress = { c, t, name -> println("[$c/$t] $name") },
    tensorFilter = { info -> info.name.startsWith("model.") }   // optional
)
runBlocking {
    loader.load(ctx, FP32::class) { name, tensor -> /* bind */ }
}
// from: SKaiNET/skainet-io/skainet-io-safetensors/src/commonMain/kotlin/sk/ainet/io/safetensors/ShardedSafeTensorsParametersLoader.kt
```

Takes the `model.safetensors.index.json` path and resolves the `model-NNNNN-of-NNNNN.safetensors` shards itself; tensors are delivered in name-sorted order regardless of shard. Unsupported-dtype failures are raised in one exception *before* any tensor is delivered (a 40-shard load should not die on tensor 900). Path-based shard resolution means it needs a file system (JVM, Android, most native targets — not JS/Wasm).

**ONNX — `OnnxLoader.fromModelSource`:**

```kotlin
import sk.ainet.io.onnx.OnnxLoader
import kotlinx.coroutines.runBlocking
import kotlinx.io.asSource
import kotlinx.io.buffered

runBlocking {
    val loader = OnnxLoader.fromModelSource {
        java.io.File("model.onnx").inputStream().asSource().buffered()
    }
    val loaded = loader.load()
    val proto = loaded.proto         // ModelProto from pbandk
    val rawBytes = loaded.rawBytes   // for re-serialisation
    // walk proto.graph.nodes / proto.graph.initializers
}
// from: SKaiNET/skainet-io/skainet-io-onnx/src/commonMain/kotlin/sk/ainet/io/onnx/OnnxLoader.kt:1-57 (public surface)
```

ONNX is a graph format — the loader hands you the protobuf representation. Lowering ONNX into a runnable SKaiNET `Module` is the next step (consumer apps typically use `skainet-compile-*` for that).

**Source factories — common idioms:**

```kotlin
import sk.ainet.io.openRandomAccessSource

// File on disk — one expect/actual for every platform (skainet-io-core).
// Returns null where the platform has no file system (JS, Wasm) or the file can't open.
val src: () -> RandomAccessSource = { openRandomAccessSource("/models/model.gguf")!! }

// Classpath resource (server-side): copy to a temp file first, then open by path —
// the random-access loaders need to seek, which a classpath stream can't.

// Android assets — see ../skainet-android-integration/SKILL.md
```

(`createRandomAccessSource` in `sk.ainet.io.gguf` is a deprecated delegate to `openRandomAccessSource`.)

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
val source = openRandomAccessSource("model.safetensors")!!
val loader = SafeTensorsParametersLoader(sourceProvider = { source })
// Now multiple loads share one already-opened source — no, the loader expects to control lifetime.
```
```kotlin
// RIGHT — open inside the lambda
val loader = SafeTensorsParametersLoader(
    sourceProvider = { openRandomAccessSource("model.safetensors")!! }
)
```

```kotlin
// WRONG — load to FP32 then cast back down
val tensor = loader.load(...)            // FP32
val small = tensor.cast<FP16, Float>()   // wastes the FP32 alloc
```
```kotlin
// RIGHT — tell the loader to keep the narrow on-disk layout
val loader = StreamingGgufParametersLoader(sourceProvider, keepF16Native = true)      // GGUF
val stl = SafeTensorsParametersLoader(
    sourceProvider = srcFactory,
    bf16Policy = NarrowFloatLoadPolicy.KEEP_NATIVE,                                   // SafeTensors BF16
)
```

```kotlin
// WRONG — the deprecated legacy facade; loadTensor throws at runtime
val reader = GGUFModelReader()
runBlocking { val w = reader.loadTensor("...") }   // error("GGUFModelReader is a legacy facade…")
```
```kotlin
// RIGHT — the streaming loader, with progress surfaced to the UI / log
val loader = StreamingGgufParametersLoader(sourceProvider, onProgress = { c, t, n -> ui.update(c, t) })
```

## References

- [`references/loaders.md`](references/loaders.md) — full signature of every loader, with the suspending / non-suspending split and the entry-point factory methods.
- [`references/format-picker.md`](references/format-picker.md) — extended decision tree for "I have a model file, which format is it and which loader?".
