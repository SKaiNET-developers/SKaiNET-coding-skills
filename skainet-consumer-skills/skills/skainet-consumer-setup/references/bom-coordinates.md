# BOM coordinates

Authoritative source: `SKaiNET/skainet-bom/build.gradle.kts`. Every artifact below is constrained by the BOM, so consumers depend on the coordinate WITHOUT a version once the BOM is added.

## BOM

| Coordinate | Notes |
|---|---|
| `sk.ainet:skainet-bom:<VERSION>` | The Bill of Materials. Add as `platform(...)`; do not depend on it as a regular library. |

## Constrained artifacts

All under group `sk.ainet.core` (one exception is the BOM itself at `sk.ainet`).

### Core language

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-lang-core` | Tensor type system, `Shape`, dtypes (`FP32`, `FP16`, `Int8`, …), the `tensor { }` and `sequential<T, V> { }` DSLs, `Module`, `ExecutionContext` interface, the Java facade objects (`SKaiNET`, `TensorJavaOps`). **Required for every consumer.** |

### Backends

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-backend-api` | `Backend` SPI; rarely depended on directly. |
| `sk.ainet.core:skainet-backend-cpu` | `DirectCpuExecutionContext.create()`, CPU op implementations, NEON / Java fallback auto-selection. **At least one backend is required.** |

### IO (model loaders)

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-io-core` | Common loader infrastructure (`RandomAccessSource`, `ModelReader`, `ParametersLoader`, progress callbacks). Required by every other `skainet-io-*` artifact. |
| `sk.ainet.core:skainet-io-gguf` | `GGUFModelReader` for GGUF files (LLM weights, tokenizer metadata, KV-cache tensors). |
| `sk.ainet.core:skainet-io-safetensors` | `SafeTensorsParametersLoader` for HuggingFace SafeTensors. |
| `sk.ainet.core:skainet-io-onnx` | `OnnxLoader<ModelProto>` for ONNX files via pbandk. |
| `sk.ainet.core:skainet-io-image` | Image decoders for input tensors (PNG/JPEG → `Tensor<FP32, Float>`). |

### Data

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-data-api` | `Dataset` / `DataBatch` abstractions. |
| `sk.ainet.core:skainet-data-simple` | Built-in toy datasets (MNIST, CIFAR-style helpers). |
| `sk.ainet.core:skainet-data-transform` | `pipeline<...>().rescale().normalize().clamp()...` preprocessing chain. |

### Compilation

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-compile-core` | `ComputeGraph` lowering, the bridge between `dag { }` and runtime / codegen. |
| `sk.ainet.core:skainet-compile-hlo` | `StableHloConverterFactory` — emits StableHLO MLIR for IREE / XLA. |

### Pipeline

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-pipeline` | Higher-level pipeline framework over `Transform` chains. |

### Models

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-model-yolo` | Pre-built YOLO architecture and pre/post-processing. |

## Not BOM-managed

The contributor-side test infrastructure (`skainet-test-groundtruth`, `skainet-test-java`) is internal-facing and not part of the consumer BOM.

## Snapshot repo

Snapshot versions (`-SNAPSHOT` suffix) live at `https://central.sonatype.com/repository/maven-snapshots/`. Stable releases are on Maven Central. Mix-and-match works: consumers can add the snapshot repo with a regex-restricted content filter so only `sk.ainet.*` artifacts are looked up there.
