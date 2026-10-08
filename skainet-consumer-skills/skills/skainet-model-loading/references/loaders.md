# Loader API reference

Authoritative sources:
- `SKaiNET/skainet-io/skainet-io-gguf/src/commonMain/kotlin/sk/ainet/io/gguf/StreamingGgufParametersLoader.kt` and `StreamingGGUFReader.kt`
- `SKaiNET/skainet-io/skainet-io-safetensors/src/commonMain/kotlin/sk/ainet/io/safetensors/SafeTensorsParametersLoader.kt` and `ShardedSafeTensorsParametersLoader.kt`
- `SKaiNET/skainet-io/skainet-io-onnx/src/commonMain/kotlin/sk/ainet/io/onnx/OnnxLoader.kt`

If signatures here disagree with the source, the source wins.

## GGUF — `StreamingGgufParametersLoader`

```kotlin
public class StreamingGgufParametersLoader(
    private val sourceProvider: () -> RandomAccessSource,
    private val onProgress: (current: Long, total: Long, message: String?) -> Unit = { _, _, _ -> },
    private val keepF16Native: Boolean = false,
    private val keepBf16Native: Boolean = false,
    private val weightForm: WeightForm? = null,                               // uniform form; null = as-stored, on-heap
    private val weightFormFor: ((tensorName: String) -> WeightForm?)? = null, // per-tensor override, wins over weightForm
    private val traceSink: TraceSink = NoopTraceSink,                         // reports load-time re-encodings
    private val i2sLayout: I2sGgufLayout = I2sGgufLayout.GROUP_128,           // BitNet I2_S bit order
) : ParametersLoader {
    public suspend fun <T : DType, V> load(
        ctx: ExecutionContext, dtype: KClass<T>,
        onTensorLoaded: (String, Tensor<T, V>) -> Unit
    )
}
```

- F32 / I32 tensors arrive dense; quantised tensors (Q4_K, Q8_0, Q4_0, Q5_0, Q5_1, Q5_K, Q6_K, …) arrive as packed block `TensorData` with their source encoding preserved.
- Fail-fast contract (#919): a file containing tensor types outside the supported set throws before any tensor is delivered, naming the offenders.
- `WeightForm(encoding, order, shape, residency)` is the one memory-intent knob: `WeightForm(residency = WeightResidency.MAPPED)` serves weights from file-backed pages (the Android default via `AndroidGguf.loader`); `EncodingRequest.DequantizeTo(FP32)` forces dense FP32.
- Companion `withPolicy(...)` builds the loader from a generalised `DTypePolicy` (e.g. `Require(FP16)` → `keepF16Native`).

### Metadata and tokenizer

```kotlin
val reader = StreamingGGUFReader.open(openRandomAccessSource(path)!!)
reader.fields["general.architecture"]       // LinkedHashMap<String, Any?> of GGUF metadata
reader.tensors                              // List<StreamingTensorInfo> — shape/dtype/offset, no payload
val tokenizer = TokenizerFactory.fromGguf(reader.fields)   // sk.ainet.io.tokenizer (skainet-io-core)
```

Memory use is proportional to metadata size (~1 MB), not file size.

### Legacy: `GGUFModelReader`

`@Deprecated` fail-fast stub — `metadata`/`tensors` are empty and `loadTensor(name)` throws. It exists only so old dependants compile; migrate to `StreamingGgufParametersLoader`.

## SafeTensors — `SafeTensorsParametersLoader`

```kotlin
public class SafeTensorsParametersLoader(
    private val sourceProvider: () -> RandomAccessSource,
    private val onProgress: (current: Long, total: Long, message: String?) -> Unit = { _, _, _ -> },
    private val bf16Policy: Bf16LoadPolicy = NarrowFloatLoadPolicy.DEQUANT_TO_FP32,
    private val fp16Policy: NarrowFloatLoadPolicy = NarrowFloatLoadPolicy.DEQUANT_TO_FP32,
    private val tensorFilter: ((StreamingSafeTensorInfo) -> Boolean)? = null,   // 0.54.0+
) : ParametersLoader {
    public suspend fun <T : DType, V> load(
        ctx: ExecutionContext, dtype: KClass<T>,
        onTensorLoaded: (String, Tensor<T, V>) -> Unit
    )
}
```

Callback-style: `onTensorLoaded` fires once per tensor, in file order. Progress: `current` and `total` are **tensor counts** (filtered tensors excluded); `message` is the tensor name. Dtype conversions: F32/F64 → FP32, I32/I64 → Int32, I8/U8 → Int8, F16/BF16 → FP32 by default or kept native via the policies (`KEEP_NATIVE` routes matmuls to the vectorised BF16 kernel — confirm dispatch support before flipping). A companion `withPolicy(sourceProvider, policy, ...)` accepts a `DTypePolicy` instead.

## Sharded SafeTensors — `ShardedSafeTensorsParametersLoader` (0.53.0+)

```kotlin
public class ShardedSafeTensorsParametersLoader(
    private val indexPath: String,                       // path to model.safetensors.index.json
    private val onProgress: (current: Long, total: Long, message: String?) -> Unit = { _, _, _ -> },
    private val bf16Policy: Bf16LoadPolicy = NarrowFloatLoadPolicy.DEQUANT_TO_FP32,
    private val fp16Policy: NarrowFloatLoadPolicy = NarrowFloatLoadPolicy.DEQUANT_TO_FP32,
    private val allowPartial: Boolean = false,           // true tolerates missing shards
    private val tensorFilter: ((ShardedTensorInfo) -> Boolean)? = null,
) : ParametersLoader
```

- Same materialisation as the single-file loader (shared `SafeTensorsMaterializer`), so both produce identical tensors for identical bytes.
- Tensors are delivered in name-sorted order regardless of which shard holds them; every shard stays open until the load completes.
- Fail-fast pre-scan: all tensors whose dtype can't materialise into the requested `DType` are reported in one `IllegalArgumentException` *before* any tensor is delivered.
- Resolves shards by path (`openRandomAccessSource`), so it needs a file system — not available on JS/Wasm.

## `OnnxLoader<M : Message>`

```kotlin
public class OnnxLoader<M : Message>(
    private val readBytes: suspend () -> ByteArray,
    private val decode: (ByteArray) -> M
) {
    public suspend fun load(): OnnxLoadedModel<M>

    public companion object {
        public fun <M : Message> fromSource(
            sourceProvider: suspend () -> Source,
            decode: (ByteArray) -> M
        ): OnnxLoader<M>

        public fun fromModelSource(
            sourceProvider: suspend () -> Source
        ): OnnxLoader<ModelProto>
    }
}

public data class OnnxLoadedModel<M : Message>(
    val proto: M,
    val rawBytes: ByteArray
)
```

`fromModelSource` is the common entry point — produces an `OnnxLoader<ModelProto>` which decodes the standard `onnx.ModelProto` from pbandk. Use the generic `fromSource` if your `.onnx` file is a different protobuf message.

`Source` is `kotlinx-io-core`'s read-only stream type; convert from a JVM `InputStream` via `inputStream.asSource().buffered()`. Note: `skainet-io-onnx` keeps kotlinx-io as an `implementation` dependency, so a consumer building the `Source` itself must declare `kotlinx-io-core` too ("Cannot access class kotlinx.io.Source" is that missing dependency; only `skainet-data-source` api-exports kotlinx-io, since 0.57.0).

To push initializer weights into a DSL-built module, `OnnxWeightLoader.applyWeights(module, tensors)` (in `skainet-io-onnx`) delegates to the format-agnostic `WeightMapper` in `sk.ainet.io.weights`.

## `ModelReader` and `ParametersLoader` interfaces

Both live in `skainet-io-core` (`sk.ainet.io`). Adding a new format means implementing one:

- `ParametersLoader` — push-style, context-bound: `suspend fun <T : DType, V> load(ctx, dtype, onTensorLoaded)`. All three production loaders (GGUF streaming, SafeTensors single + sharded) implement it.
- `ModelReader` — pull-style (`metadata`, `tensors`, `loadTensor(name)`); legacy surface, kept for compatibility.

`OnnxLoader` is a concrete class rather than either interface because of the protobuf-message generic.

## Source types

| Type | Where from |
|---|---|
| `RandomAccessSource` | `sk.ainet.io` (`skainet-io-core`). Positional-read byte source — required by SafeTensors and GGUF (need to seek). |
| `kotlinx.io.Source` | `kotlinx-io-core`. Sequential read-only stream — sufficient for ONNX (parse once). |

`openRandomAccessSource(filePath)` in `sk.ainet.io` is the one `expect`/`actual` factory for every platform (#1037): `JvmRandomAccessSource` on the JVM, `AndroidRandomAccessSource` (positional `FileChannel` reads) on Android, `pread(2)`-based sources on native; returns `null` on platforms without a file system (JS, Wasm) so callers can fall back to sequential whole-file loading. The per-format `createRandomAccessSource` functions are deprecated delegates to it.
