# Artifact picker

Decision tree for "I need to do X, what should I add?". Always implies `sk.ainet.core:skainet-lang-core` + one backend (CPU is default) is already in place.

## Inference scenarios

### "Run a small model I built with `sequential<T, V> { }` directly"

You don't need anything beyond `skainet-lang-core` + `skainet-backend-cpu`. Construct the model in code, optionally load weights from a file (next sections), call `model.forward(x, ctx)`.

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

The training context comes from the same `DirectCpuExecutionContext` with `phase = Phase.TRAIN`.

## Compilation / export scenarios

### "Export a DAG to StableHLO MLIR for IREE"

```
+ skainet-compile-core
+ skainet-compile-hlo
```

### "Generate C99 code for embedded targets"

```
+ skainet-compile-core
+ skainet-compile-c        # check coordinates - currently part of contributor build, may need direct module dep
```

(C99 codegen is currently shipped as a SKaiNET-internal module; for now consumers building C99 may need to clone and `composite-build` until/if it's promoted.)

## Multi-target scenarios

### "Use SKaiNET in commonMain across JVM + Android + iOS"

Common code should depend ONLY on `skainet-lang-core` (and any data/transform modules that are KMP-published). Backends are platform-specific:

- `jvmMain`, `androidMain` → `skainet-backend-cpu`
- `iosArm64Main`, `iosSimulatorArm64Main` → `skainet-backend-cpu` (Native target ships)
- `wasmJsMain`, `wasmWasiMain` → `skainet-backend-cpu`

### "I'm Java-only (Spring Boot, Android Java, …)"

See [`../skainet-java-consumer/SKILL.md`](../skainet-java-consumer/SKILL.md). The artifact set is a JVM-only subset; the consumer doesn't depend on `skainet-data-simple` (which has Android-specific cinterop) unless explicitly needed.

## "Why isn't X resolving?"

| Symptom | Likely cause |
|---|---|
| `Unresolved reference: DirectCpuExecutionContext` | Missing `skainet-backend-cpu`. |
| `Unresolved reference: GGUFModelReader` | Missing `skainet-io-gguf`. |
| `Could not find sk.ainet:skainet-bom:0.20.0-SNAPSHOT` | Snapshot version without the snapshot repo configured. |
| Resolver picks an old version of `kotlinx-coroutines` | Add the BOM (`platform(...)`) — without it the consumer's other libraries can drag in mismatched transitives. |
| Build passes but native targets fail at link | Backend not added to that target's source set; KMP consumer needs the backend in every target it actually runs on. |
