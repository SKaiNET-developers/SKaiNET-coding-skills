# TurboQuant

Authoritative sources: `SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/ops/turboquant/TurboQuantCodec.kt` (plus `TurboQuantPresets.kt`, `TurboQuantUsage.kt` in the same package) and `.../sk/ainet/lang/tensor/storage/TensorEncoding.kt`, `.../storage/KvCacheStore.kt`.

## What it is

Runtime KV-cache compression using rotation-based quantisation (after the TurboQuant paper): compress K/V projections on write, decompress on read. No model retraining or weight re-quantisation — any model benefits immediately. Two flavours:

- **Polar (default)** — rotation + scalar quantisation + bit-packing. Bits per element 2, 3, 4 or 8; block size a power of 2 (typically 64 or 128).
- **Polar + QJL** — adds a QJL residual stage (`residualBits`, 1–4, typically 1). Closest to the paper; better inner-product accuracy at extra storage cost.

## Encodings

In `sk.ainet.lang.tensor.storage.TensorEncoding` (sealed hierarchy alongside `Q4_K`, `Q8_0`, …):

```kotlin
public data class TurboQuantPolar(
    val bitsPerElement: Int = 4,     // must be 2, 3, 4 or 8
    val blockSize: Int = 128         // positive power of 2
) : TensorEncoding {
    override val name: String        // "TurboQuant-Polar-4b"
}

public data class TurboQuantPolarQjl(
    val bitsPerElement: Int = 4,
    val residualBits: Int = 1,       // 1..4
    val blockSize: Int = 128
) : TensorEncoding {
    override val name: String        // "TurboQuant-PolarQjl-4b+1r"
}
```

Plug them into a `KvCacheConfig` (`keyEncoding` / `valueEncoding`) — the KV-cache store applies them at the storage layer.

## KV-cache stores and presets

```kotlin
import sk.ainet.lang.tensor.storage.KvCacheStore

// Named preset: "safe-lowbit", "balanced", "experimental-max"
val cache = KvCacheStore.turboQuant(
    preset = "balanced", numLayers = 32, numHeads = 32, headDim = 128, maxSeqLen = 4096
)

// Custom bit budgets (asymmetric K/V is the point):
val cache2 = KvCacheStore.turboQuant(
    numLayers = 32, numHeads = 32, headDim = 128, maxSeqLen = 4096,
    keyBits = 8, valueBits = 4, useQjl = false
)

// Uncompressed FP32 baseline for quality comparison:
val dense = KvCacheStore.dense(numLayers = 32, numHeads = 32, headDim = 128, maxSeqLen = 4096)
```

Presets (`TurboQuantPresets`) encode the observation that key precision is more quality-sensitive than value precision:

| Preset | Keys | Values |
|---|---|---|
| `safe-lowbit` | Q8_0 | TurboQuant-4 |
| `balanced` | TurboQuant-4 | TurboQuant-4 |
| `experimental-max` | TurboQuant-3 | TurboQuant-3 |

The backing implementations are `TurboQuantKvCacheStore` / `DefaultKvCacheStore` (`appendToken(layer, key, value)`, `memoryReport()`). See `TurboQuantUsage.kt` in the source for the full integration guide.

## Codec

```kotlin
public data class TurboQuantConfig(
    val bits: Int = 4,
    val useQjl: Boolean = false,
    val residualBits: Int = 1,
    val seed: Int = 0
) {
    public companion object {
        public fun polarOnly(bits: Int = 4, seed: Int = 0): TurboQuantConfig
        public fun polarPlusQjl(bits: Int = 4, residualBits: Int = 1, seed: Int = 0): TurboQuantConfig
    }
}

public object TurboQuantCodec {
    public fun encode(input: FloatArray, config: TurboQuantConfig): TurboQuantBlock
    public fun decode(block: TurboQuantBlock): FloatArray
    public fun encodedSize(elementCount: Int, config: TurboQuantConfig): Int
}
```

Use `TurboQuantCodec` directly when you want raw FloatArray ↔ block transitions outside the tensor system (`TurboQuantBlock` carries `packedCodes`, `scales`, `seed`, `bits`, `elementCount`, optional `residual`; `sizeInBytes` reports the footprint). For KV-cache use, prefer the `KvCacheStore` factories above. On the JVM, the hot paths are SIMD-accelerated (`JvmTurboQuantKernels`, Java Vector API).

## Picking bits

| Bits | Compression | Quality |
|---|---|---|
| 2 | ≈16× | Aggressive — measurable accuracy loss; use only with QJL residual and on tensors you've evaluated. |
| 3 | ≈10× | Aggressive (`experimental-max`); QJL recommended. |
| 4 | ≈8× | Sweet spot for KV cache. Low quality loss, large memory savings. |
| 8 | ≈4× | Near-lossless on most workloads. Default for keys in `safe-lowbit` (as Q8_0). |

Block size 128 is the default and rarely needs changing (must be a power of 2). Larger blocks compress better but degrade quality on heterogeneous tensors; smaller blocks are inverse.

## Where consumers apply it

- **KV cache in transformer inference** (the designed use case): 4-bit polar keys+values — typical ~8× memory reduction with minimal accuracy impact.
- **Activation cache in beam search / iterative decoding**: encode intermediate states via the codec.

Don't encode inputs or outputs that the consumer needs to read in raw FP32 form — encoding rounds, and you'll see drift. For *weight* compression, prefer the GGUF block formats (Q4_K, Q8_0, …) that the loaders preserve as packed storage — TurboQuant is aimed at the runtime KV cache.

## Determinism

`seed` controls the randomised rotation basis (stored per block). Same seed → same encoding result for the same input. Use a fixed seed in tests; in production it's typically fine to leave the default 0.
