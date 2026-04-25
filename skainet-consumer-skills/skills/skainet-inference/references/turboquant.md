# TurboQuant

Authoritative source: `SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/ops/turboquant/TurboQuantCodec.kt` and surrounding files in the same package.

## What it is

A polar-coordinates quantisation scheme tuned for KV cache and weight compression. Two flavours:

- **Polar (default)** — uniform polar quantisation. Configurable bit width (2, 3, 4, 8) per element; configurable block size (typically 128).
- **Polar + QJL** — polar with a residual correction (`residualBits`, typically 1) for higher quality at marginal cost.

## Encodings

```kotlin
public data class TurboQuantPolar(
    val bitsPerElement: Int = 4,
    val blockSize: Int = 128
) : TensorEncoding {
    override val name: String   // "TurboQuant-Polar-4b"
}

public data class TurboQuantPolarQjl(
    val bitsPerElement: Int = 4,
    val residualBits: Int = 1,
    val blockSize: Int = 128
) : TensorEncoding {
    override val name: String   // "TurboQuant-PolarQjl-4b+1r"
}
```

Plug into a `TensorSpec` (or directly into KV-cache storage) to apply at the storage layer.

## Codec

```kotlin
public data class TurboQuantConfig(
    val bits: Int = 4,
    val seed: Int = 0,
    val useQjl: Boolean = false,
    val residualBits: Int = 1
) {
    public companion object {
        public fun polarOnly(bits: Int = 4, seed: Int = 0): TurboQuantConfig
        public fun polarPlusQjl(bits: Int = 4, residualBits: Int = 1, seed: Int = 0): TurboQuantConfig
    }
}

public object TurboQuantCodec {
    public fun encode(input: FloatArray, config: TurboQuantConfig): TurboQuantBlock
    public fun decode(block: TurboQuantBlock): FloatArray
}
```

Use `TurboQuantCodec` directly when you want raw FloatArray ↔ block transitions outside the tensor system. For tensor-level encoding, attach a `TurboQuantPolar` / `TurboQuantPolarQjl` to a `TensorSpec` and let the storage layer handle it.

## Picking bits

| Bits | Compression | Quality |
|---|---|---|
| 2 | ≈16× | Aggressive — measurable accuracy loss; use only with QJL residual and on tensors you've evaluated. |
| 3 | ≈10× | Aggressive; QJL recommended. |
| 4 | ≈8× | Sweet spot for KV cache. Low quality loss, large memory savings. |
| 8 | ≈4× | Near-lossless on most workloads. Default for sensitive tensors (e.g. attention weights). |

Block size 128 is the default and rarely needs changing. Larger blocks compress better but degrade quality on heterogeneous tensors; smaller blocks are inverse.

## Where consumers apply it

- **KV cache in transformer inference**: encode keys + values to 4-bit polar — typical ~8× memory reduction with minimal accuracy impact.
- **Weights of large layers** that are read-only at inference: encode at load time; trade load time + storage size for memory footprint at runtime.
- **Activation cache in beam search / iterative decoding**: encode intermediate states.

Don't encode inputs or outputs that the consumer needs to read in raw FP32 form — encoding rounds, and you'll see drift.

## Determinism

`seed` controls QJL's randomised residual basis. Same seed → same encoding result for the same input. Use a fixed seed in tests; in production it's typically fine to leave the default 0.
