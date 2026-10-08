# BOM coordinates

Authoritative source: `SKaiNET/skainet-bom/build.gradle.kts` + the `sk.ainet.transformers.bom-coverage` convention plugin. The BOM's constraints are auto-populated: every sibling subproject that applies the publish plugin is added as an `api` constraint. Consumers depend on the coordinates WITHOUT a version once the BOM is added.

## BOM

| Coordinate | Notes |
|---|---|
| `sk.ainet:skainet-bom:<VERSION>` | The Bill of Materials. Add as `platform(...)`; do not depend on it as a regular library. |

## Constrained artifacts

All under group `sk.ainet.core` (one exception is the BOM itself at `sk.ainet`).

### Core language

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-lang-core` | Tensor type system, `Shape`, dtypes (`FP32`, `FP16`, `Int8`, …), the `tensor { }` and `sequential<T, V> { }` DSLs, `Module`, `ExecutionContext` interface, the Java facade (`TensorJavaOps`, `SequentialModelBuilder`, `Optimizers`, `Losses`, `TrainingLoop`). **Required for every consumer.** |
| `sk.ainet.core:skainet-lang-dag` | The `dag { }` graph DSL (`sk.ainet.lang.dag.GraphDsl`), tracing to `GraphProgram`, schedule / dtype-policy DSLs. |
| `sk.ainet.core:skainet-lang-models` | `Model` / `ModelCard` / `ModelLoader` abstractions over architecture + weights + loading state. |
| `sk.ainet.core:skainet-lang-ksp-annotations` | Annotations consumed by the KSP processor; `skainet-lang-core` already exposes it via `api`, so consumers rarely add it directly. |
| `sk.ainet.core:skainet-lang-ksp-processor` | The KSP processor itself (build-time, `ksp(...)` configuration). |

### Backends

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-backend-api` | `Backend` SPI and kernel-provider contracts; rarely depended on directly. |
| `sk.ainet.core:skainet-backend-cpu` | `DirectCpuExecutionContext.create()`, CPU op implementations. **At least one backend is required.** |
| `sk.ainet.core:skainet-backend-native-cpu` | Hand-tuned C/NEON kernels reached via the Java FFM API on the JVM (plus published Kotlin/Native klibs). JVM side is JVM-only — add to `jvmMain.dependencies`, never `commonMain`. Auto-registers via ServiceLoader. |
| `sk.ainet.core:skainet-backend-jni-cpu` | Android JNI bridge (AAR) to the same native kernels — ART has no FFM, so Android goes through JNI. |

### IO (model loaders)

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-io-core` | Common loader infrastructure (`RandomAccessSource`, `ModelReader`, `ParametersLoader`, progress callbacks) plus `TokenizerFactory` (`sk.ainet.io.tokenizer`). Required by every other `skainet-io-*` artifact. |
| `sk.ainet.core:skainet-io-gguf` | `GGUFModelReader` for GGUF files (LLM weights, tokenizer metadata, KV-cache tensors). |
| `sk.ainet.core:skainet-io-safetensors` | `SafeTensorsParametersLoader` for HuggingFace SafeTensors (incl. sharded checkpoints). |
| `sk.ainet.core:skainet-io-onnx` | `OnnxLoader` for ONNX files via pbandk. |
| `sk.ainet.core:skainet-io-image` | Image decoders for input tensors (PNG/JPEG → tensors). |
| `sk.ainet.core:skainet-io-iree-params` | `IrpaWriter` — writes IREE Parameter Archive (`.irpa`) files for IREE deployment. |

### Data

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-data-api` | `Dataset` / `DataBatch` abstractions (shuffle, split, filter views). |
| `sk.ainet.core:skainet-data-simple` | Built-in toy datasets (MNIST, CIFAR-style helpers). |
| `sk.ainet.core:skainet-data-source` | URI-backed data sources (`file://`, `https://`, `hf://owner/repo/path`), `rawDataset { }` + `dataPipeline<T>()` DSLs, CSV/TSV/JSON/JSONL parsers, caching via `CachePolicy`. |
| `sk.ainet.core:skainet-data-transform` | `pipeline<...>().rescale().normalize().clamp()...` preprocessing chain. |

### Compilation

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-compile-core` | `ComputeGraph` lowering, the bridge between graph programs and runtime / codegen. |
| `sk.ainet.core:skainet-compile-dag` | DAG compilation: `ComputeGraph` construction from traces, autograd / graph inversion. |
| `sk.ainet.core:skainet-compile-opt` | Per-phase, per-target compile optimization passes (`TargetOptimizer`, `TargetOptimizers` registry, output pruning). |
| `sk.ainet.core:skainet-compile-hlo` | `StableHloConverterFactory` — emits StableHLO MLIR for IREE / XLA. |
| `sk.ainet.core:skainet-compile-c` | C99 code generation for embedded targets. |
| `sk.ainet.core:skainet-compile-json` | JSON export of compiled graphs. |
| `sk.ainet.core:skainet-compile-minerva` | Minerva secure-MCU export. |

### Pipeline

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-pipeline` | Higher-level pipeline framework (`Pipeline`, `PipelineBuilder`, node/edge graph). |

### Models

| Coordinate | Provides |
|---|---|
| `sk.ainet.core:skainet-model-yolo` | Pre-built YOLO architecture and pre/post-processing. |

## Not BOM-managed

- The in-repo test infrastructure (`skainet-test-groundtruth`, `skainet-test-java`) does not apply the publish plugin — it is not published and not in the BOM.
- `skainet-data-media` exists in the repo but is not published either (no publish plugin as of 0.57.0).

## Snapshot repo

Snapshot versions (`-SNAPSHOT` suffix) live at `https://central.sonatype.com/repository/maven-snapshots/`. Stable releases are on Maven Central. Mix-and-match works: consumers can add the snapshot repo with a regex-restricted content filter so only `sk.ainet.*` artifacts are looked up there.
