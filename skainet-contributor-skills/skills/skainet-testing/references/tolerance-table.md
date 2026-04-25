# Tolerance table

Authoritative source: `SKaiNET/skainet-test/skainet-test-groundtruth/src/commonMain/kotlin/sk/ainet/test/groundtruth/TensorAssertions.kt:14-44`. If the table here disagrees with `ToleranceConfig.forOperation`, the source wins — update this file.

## Constants

| Name | Value | Use for |
|---|---|---|
| `STRICT` | `1e-6f` | Pure arithmetic, exact transformations (`add`, `subtract`, `multiply`, `divide`, `relu`, `leakyRelu`, `flatten`, `reshape`). |
| `STANDARD` | `1e-5f` | Multi-step linear-algebra ops (`matmul`, `conv1d`, `conv2d`, `conv3d`) and reductions (`sum`, `mean`, `variance`). Default for unknown ops. |
| `RELAXED` | `1e-4f` | Transcendentals and normalisations (`sigmoid`, `gelu`, `silu`, `softmax`, `logSoftmax`). |
| `GRADIENT` | `1e-4f` | Anything in a backward pass / autograd check (operation name contains `grad`). |
| `VERY_RELAXED` | `1e-3f` | Reserved for ops with documented numerical instability — needs a comment justifying its use. |

## Picker (mirrors `ToleranceConfig.forOperation`)

```kotlin
when {
    op in listOf("add", "subtract", "multiply", "divide") -> STRICT
    op in listOf("matmul", "conv2d", "conv1d", "conv3d") -> STANDARD
    op in listOf("relu", "leakyRelu", "flatten", "reshape") -> STRICT
    op in listOf("sigmoid", "gelu", "silu", "softmax", "logSoftmax") -> RELAXED
    op in listOf("sum", "mean", "variance") -> STANDARD
    op.contains("grad") -> GRADIENT
    else -> STANDARD
}
// from: SKaiNET/skainet-test/skainet-test-groundtruth/src/commonMain/kotlin/sk/ainet/test/groundtruth/TensorAssertions.kt:33-43
```

## Picking by hand

1. Single-pass arithmetic on FP32 → `STRICT`.
2. Anything that traverses a kernel or accumulates → `STANDARD`.
3. Anything with `exp` / `log` in its definition → `RELAXED`.
4. Any backward / gradient check → `GRADIENT`.
5. Forced to use `VERY_RELAXED`? Document why directly above the call site.

## Relative tolerance

`assertTensorClose` and `assertArrayClose` accept an `rtol` (default `1e-5f`). The comparison rule is `|a − b| <= atol + rtol * max(|a|, |b|)`. Override `rtol` only when the values being compared can have very different magnitudes inside one tensor and you have already picked `atol` correctly.
