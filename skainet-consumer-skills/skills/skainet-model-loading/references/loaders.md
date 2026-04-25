# Loader API reference

Authoritative sources:
- `SKaiNET/skainet-io/skainet-io-gguf/src/commonMain/kotlin/sk/ainet/io/gguf/GGUFModelReader.kt`
- `SKaiNET/skainet-io/skainet-io-safetensors/src/commonMain/kotlin/sk/ainet/io/safetensors/SafeTensorsParametersLoader.kt`
- `SKaiNET/skainet-io/skainet-io-onnx/src/commonMain/kotlin/sk/ainet/io/onnx/OnnxLoader.kt`

If signatures here disagree with the source, the source wins.

## `GGUFModelReader`

```kotlin
public class GGUFModelReader : ModelReader {
    public override val metadata: Map<String, Any>
    public override val tensors: Map<String, TensorInfo>
    public override suspend fun loadTensor(name: String): TensorData<*, *>
    public override fun close()
}
```

Construct with a source provider (the exact constructor signature varies by version; check the source). Stream tensors one at a time via `loadTensor(name)`. Use `metadata` for `gguf.architecture`, vocab, special tokens, and `tensors` for per-tensor shape/dtype info.

The `TokenizerFactory.fromGguf(metadata)` Java helper (in `skainet-compile-hlo`) builds a tokenizer from the GGUF metadata map.

## `SafeTensorsParametersLoader`

```kotlin
public class SafeTensorsParametersLoader(
    private val sourceProvider: () -> RandomAccessSource,
    private val onProgress: (current: Long, total: Long, message: String?) -> Unit = { _, _, _ -> }
) : ParametersLoader {

    public override suspend fun <T : DType, V> load(
        ctx: ExecutionContext,
        dtype: KClass<T>,
        onTensorLoaded: (name: String, tensor: Tensor<T, V>) -> Unit
    )
}
```

Callback-style: `onTensorLoaded` fires once per tensor, in file order. Progress: `current` and `total` are byte counts; `message` is the tensor name being parsed.

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

public class OnnxLoadedModel<M : Message>(
    public val proto: M,
    public val rawBytes: ByteArray
)
```

`fromModelSource` is the common entry point — produces an `OnnxLoader<ModelProto>` which decodes the standard `onnx.ModelProto` from pbandk. Use the generic `fromSource` if your `.onnx` file is a different protobuf message.

`Source` is `kotlinx-io-core`'s read-only stream type; convert from JVM `InputStream` via `inputStream.asSource()`, from `kotlin-io` `Buffer` via direct construction.

## `ModelReader` and `ParametersLoader` interfaces

Both live in `skainet-io-core`. Adding a new format means implementing one or both:

- `ModelReader` — graph + weights + metadata; suitable for formats like ONNX (full graph) or GGUF (weights + metadata).
- `ParametersLoader` — weights only; suitable for formats like SafeTensors that ship raw tensors without a graph.

`OnnxLoader` is currently structured as a concrete class rather than `ModelReader` because of the protobuf-message generic.

## Source types

| Type | Where from |
|---|---|
| `RandomAccessSource` | `skainet-io-core`. Random-access byte source — required by SafeTensors and GGUF (need to seek). |
| `kotlinx.io.Source` | `kotlinx-io-core`. Sequential read-only stream — sufficient for ONNX (parse once). |

`RandomAccessSourceFactory` is `expect`/`actual` per platform (`commonMain` declares; `jvmMain` / `androidMain` / native targets implement). Consumers normally don't construct these directly — pass a path or a stream and let the platform pick.
