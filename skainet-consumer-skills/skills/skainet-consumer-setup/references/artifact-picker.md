# Artifact picker

Decision tree for "I need to do X, what should I add?". Always implies `sk.ainet.core:skainet-lang-core` + one backend (CPU is default) is already in place.

## Inference scenarios

### "Run a small model I built with `sequential<T, V> { }` directly"

You don't need anything beyond `skainet-lang-core` + `skainet-backend-cpu`. Construct the model in code, optionally load weights from a file (next sections), call `model.forward(x, ctx)`.

If the model is a `dag { }` graph program instead of a `sequential` stack, add `skainet-lang-dag` (the graph DSL lives there, not in `skainet-lang-core`).

### "Load a Hugging Face model in SafeTensors format"

```
+ skainet-io-core
+ skainet-io-safetensors
```

### "Run a converted ONNX model"

```
+ skainet-io-core
+ skainet-io-onnx
```

### "Run an LLM checkpoint (GGUF)"

```
+ skainet-io-core
+ skainet-io-gguf
```

Likely also wants TurboQuant for KV-cache compression — that's already in `skainet-lang-core`, no new dep.

### "Pre-process images before inference (rescale, normalise, batch)"

```
+ skainet-data-transform
+ skainet-io-image  # if decoding from a file
```

### "Run YOLO out of the box"

```
+ skainet-model-yolo
+ skainet-io-core
+ skainet-io-gguf  (or whichever format the YOLO checkpoint is in)
+ skainet-io-image
+ skainet-data-transform
```

## Training scenarios

### "Train a model from scratch"

```
+ skainet-data-api          # Dataset / DataBatch
+ skainet-data-simple       # toy datasets if you need them
+ skainet-data-transform    # preprocessing
```

The training context comes from the same `DirectCpuExecutionContext` with `phase = Phase.TRAIN` (`DirectCpuExecutionContext.create(Phase.TRAIN)`).

### "Load training data from files, URLs, or the Hugging Face Hub"

```
+ skainet-data-source       # rawDataset { from("hf://owner/repo/data.csv") }, CSV/TSV/JSON/JSONL parsers, caching
```

## Compilation / export scenarios

### "Export a DAG to StableHLO MLIR for IREE"

```
+ skainet-compile-core
+ skainet-compile-hlo
```

### "Generate C99 code for embedded targets"

```
+ skainet-compile-core
+ skainet-compile-c
```

`sk.ainet.core:skainet-compile-c` is published and BOM-managed. Related export targets: `skainet-compile-json` (JSON graph export), `skainet-compile-minerva` (Minerva secure-MCU export), `skainet-io-iree-params` (`IrpaWriter` for IREE `.irpa` parameter archives).

## Multi-target scenarios

### "Use SKaiNET in commonMain across JVM + Android + iOS"

Common code should depend ONLY on `skainet-lang-core` (and any data/transform modules that are KMP-published). Backends are platform-specific:

- `jvmMain`, `androidMain` → `skainet-backend-cpu`
- `iosArm64Main`, `iosSimulatorArm64Main` → `skainet-backend-cpu` (Native target ships)
- `wasmJsMain`, `wasmWasiMain` → `skainet-backend-cpu`

### "I want the hand-tuned native CPU kernels"

- JVM (desktop/server): add `skainet-backend-native-cpu` to `jvmMain.dependencies` — it reaches the C/NEON kernels through the Java FFM API and auto-registers via ServiceLoader. It is JVM-only on that path; adding it to `commonMain` breaks the Native/JS/Wasm targets.
- Android: add `skainet-backend-jni-cpu` (AAR) — ART has no FFM, so Android goes through JNI.
- Since 0.52.0 the kernel packs self-install on first use (`KernelDispatch.ensureInstalled()`); no startup install call is needed.

### "I'm Java-only (Spring Boot, Android Java, …)"

See [`../skainet-java-consumer/SKILL.md`](../skainet-java-consumer/SKILL.md). The artifact set is a JVM-only subset of the same coordinates.

## "Why isn't X resolving?"

| Symptom | Likely cause |
|---|---|
| `Unresolved reference: DirectCpuExecutionContext` | Missing `skainet-backend-cpu`. |
| `Unresolved reference: GGUFModelReader` | Missing `skainet-io-gguf`. |
| `Unresolved reference: dag` | Missing `skainet-lang-dag` (the `dag { }` DSL is not in `skainet-lang-core`). |
| `Could not find sk.ainet:skainet-bom:<X>-SNAPSHOT` | Snapshot version without the snapshot repo configured. |
| `UnsupportedClassVersionError` / "class file version 65.0" | Running on a JVM older than 21 — published JVM jars are Java 21 bytecode. |
| Resolver picks an old version of `kotlinx-coroutines` | Add the BOM (`platform(...)`) — without it the consumer's other libraries can drag in mismatched transitives. |
| Build passes but native targets fail at link | Backend not added to that target's source set; KMP consumer needs the backend in every target it actually runs on. |
