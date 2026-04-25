---
name: skainet-data-dsl
description: Use when constructing tensors, slicing them, or building transform pipelines using the SKaiNET public DSL — applies in both consumer apps and inside the SKaiNET repo. Trigger tokens include `tensor(`, `tensor {`, `data<`, `pipeline<`, `sliceView`, `segment {`, `rescale`, `normalize`, `unsqueeze` (in pipeline context), `FP32::class`, `FP16::class`, `Int8::class`, `Int32::class`, `Ternary::class`, `randn(`, `uniform(`. Do NOT fire on tensor *assertions* (in-repo tests go to the contributor `skainet-testing` skill) or on neural-network builders (`sequential` / `dag` go to `skainet-nn-dsl`).
version: 0.1.0
---

# skainet-data-dsl

Building blocks for tensor data: creation, initialisation, slicing, and transform pipelines for preprocessing. This skill is a cheatsheet — DSL skills teach usage rather than enforce constraints.

## When to use

- Constructing a tensor literal with a known shape and fill (zeros, ones, fill, random, fromArray).
- Slicing or viewing an existing tensor.
- Building a preprocessing pipeline (rescale → normalize → unsqueeze → reshape).
- Choosing a dtype tag (`FP32`, `FP16`, `Int8`, `Int32`, `Int4`, `Ternary`).

## When NOT to use

- Asserting on tensor values in tests — `skainet-testing`.
- Defining neural network architecture with `sequential { }` / `dag { }` — `skainet-nn-dsl`.
- Exposing a tensor builder to Java — `skainet-java-interop`.
- Editing where a tensor file lives in source sets — `kmp`.

## Cheatsheet

### Two equivalent tensor entry points

```kotlin
// (a) Direct entry — tensor(executionContext, dtypeKClass) { ... }
val t = tensor<FP32, Float>(ctx, FP32::class) {
    tensor {
        shape(2, 3) {
            from(0f, 1f, 2f, 10f, 11f, 12f)
        }
    }
}
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/dsl/TensorDSL.kt:17-25
```

```kotlin
// (b) Phase-aware entry — data<T, V>(ctx) { tensor { ... } }
val t = data<FP32, Float>(ctx) {
    tensor {
        shape(2, 3) {
            from(0f, 1f, 2f, 10f, 11f, 12f)
        }
    }
}
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonTest/kotlin/sk/ainet/readme/ReadmeSnippetsTest.kt:18-32
```

Use form (b) when you're already inside a phase-aware execution context (training vs eval) and want phase-tagged tensors. Use form (a) for plain inference / tests / examples.

### Initialisation strategies inside `shape(...) { ... }`

```kotlin
shape(28, 28) { zeros() }           // FloatArray of zeros
shape(28, 28) { ones() }
shape(28, 28) { full(0.5f) }        // every element = 0.5
shape(2, 3)   { from(1f, 2f, 3f, 4f, 5f, 6f) }  // explicit values, length must equal shape volume
shape(2, 3)   { fromArray(myFloatArray) }
shape(28, 28) { randn(mean = 0f, std = 0.02f) }
shape(28, 28) { uniform(min = -1f, max = 1f) }
shape(28, 28) { init { idx -> (idx[0] + idx[1]).toFloat() } }
shape(28, 28) { randomInit({ rng -> rng.nextFloat() }) }
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/dsl/TensorDSL.kt:50-108
```

### Slice views — `sliceView { segment { ... } }`

```kotlin
val view = bigTensor.sliceView {
    segment { range(0, 10) }      // dim 0: indices 0..9 (exclusive end)
    segment { at(5) }             // dim 1: pick exactly index 5
    segment { all() }             // dim 2: keep everything
    segment { step(0, 20, 2) }    // dim 3: every 2nd index from 0 to 20
}
// from: SKaiNET/skainet-lang/skainet-lang-core/src/commonMain/kotlin/sk/ainet/lang/tensor/TensorSliceBuilder.kt:18-26
```

The number of `segment { }` blocks MUST equal the rank of the tensor — `validate(tensorShape)` throws otherwise.

### Transform pipelines

```kotlin
val preprocess = pipeline<Tensor<FP32, Float>>()
    .rescale(ctx, scale = 255f)
    .normalize(ctx, mean = imagenetMean, std = imagenetStd, channelAxis = -1)
    .unsqueeze(0)                 // add batch dim at position 0

val batch = preprocess(rawImageTensor)
// from: SKaiNET/skainet-data/skainet-data-transform/src/commonMain/kotlin/sk/ainet/data/transform/TensorTransformDsl.kt:18-50
```

Available transform extensions: `rescale`, `normalize`, `scaleAndShift`, `clamp`, `reshape` (more to follow — file is the source of truth).

### Dtype tags

| Tag | Native value type `V` | Use |
|---|---|---|
| `FP32` | `Float` | default; training, inference, ground truth |
| `FP16` | `Float` (promoted) | half precision inference |
| `Int32` | `Int` | indices, labels |
| `Int8` | `Byte` | quantised inference |
| `Int4` | `Byte` (promoted) | aggressive quantisation |
| `Ternary` | `Byte` | -1/0/+1 weights |

`tensor<FP32, Float>(...)` — the value-type parameter follows the table above. `tensor<FP32, Int>(...)` will not type-check.

## Workflow

1. Decide whether the tensor is part of a phase (training-aware) or a plain literal — pick `tensor(...) { tensor { } }` or `data(...) { tensor { } }` accordingly.
2. Pick the dtype + value-type pair from the table.
3. Pick the initialisation: deterministic literals (`from`, `fromArray`, `full`) for tests; `randn` / `uniform` for parameter init; `init` / `randomInit` for custom generators.
4. For preprocessing chains, compose transforms in `pipeline<...>()` — every step takes the `ExecutionContext` so the tensors land in the right backend.
5. Reach for `sliceView { segment { ... } }` only when the operation isn't already covered by a tensor-op like `narrow`, `unsqueeze`, `squeeze`, `flatten` (those are simpler and cheaper).

## Related skills

- The `ExecutionContext` itself comes from `DirectCpuExecutionContext.create()` (CPU) or `DefaultNeuralNetworkExecutionContext()` for the phase-aware form — see [`../skainet-inference/SKILL.md`](../skainet-inference/SKILL.md).
- Feeding the tensor into a network — see [`../skainet-nn-dsl/SKILL.md`](../skainet-nn-dsl/SKILL.md).
- Adding the SKaiNET dependency that exposes `tensor { }` to your Gradle project — see [`../skainet-consumer-setup/SKILL.md`](../skainet-consumer-setup/SKILL.md).
- Calling these from Java — see [`../skainet-java-consumer/SKILL.md`](../skainet-java-consumer/SKILL.md).
- (In-repo only) Comparing computed tensors against expected values in tests — see the contributor `skainet-testing` skill.

## Anti-patterns

```kotlin
// WRONG — wrong value-type for the dtype
val t = tensor<FP32, Int>(ctx, FP32::class) { tensor { shape(2) { from(1, 2) } } }
```
```kotlin
// RIGHT — match the dtype/value-type table
val t = tensor<FP32, Float>(ctx, FP32::class) { tensor { shape(2) { from(1f, 2f) } } }
val ti = tensor<Int32, Int>(ctx, Int32::class) { tensor { shape(2) { from(1, 2) } } }
```

```kotlin
// WRONG — manually slicing with index loops in user code
val rows = (0 until 10).map { i -> bigTensor[i] }
```
```kotlin
// RIGHT — sliceView
val rows = bigTensor.sliceView { segment { range(0, 10) }; segment { all() } }
```

```kotlin
// WRONG — chained scalar ops to do preprocessing
val x1 = raw.ops.divScalar(raw, 255f)
val x2 = x1.ops.subScalar(x1, mean)
val x3 = x2.ops.divScalar(x2, std)
```
```kotlin
// RIGHT — a transform pipeline
val pre = pipeline<Tensor<FP32, Float>>()
    .rescale(ctx, 255f)
    .normalize(ctx, floatArrayOf(mean), floatArrayOf(std))
val out = pre(raw)
```

## References

- [`references/tensor-builders.md`](references/tensor-builders.md) — every entry point on `TensorCreationScope` and `ShapeBuilder`, with signatures.
- [`references/transform-ops.md`](references/transform-ops.md) — every transform extension function in `skainet-data-transform`, with arguments and defaults.
