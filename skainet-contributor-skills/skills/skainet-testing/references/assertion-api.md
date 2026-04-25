# TensorAssertions API

Authoritative source: `SKaiNET/skainet-test/skainet-test-groundtruth/src/commonMain/kotlin/sk/ainet/test/groundtruth/TensorAssertions.kt`. All signatures below match that file. Update on any drift.

## `compare(...)` — non-throwing

```kotlin
TensorAssertions.compare(
    expected: FloatArray,
    actual: FloatArray,
    expectedShape: Shape,
    actualShape: Shape,
    atol: Float = ToleranceConfig.STANDARD,
    rtol: Float = 1e-5f
): ComparisonResult
// from: TensorAssertions.kt:131-138

TensorAssertions.compare(
    expected: GroundTruthTensor,
    actual: Tensor<T, V>,
    atol: Float = ToleranceConfig.STANDARD,
    rtol: Float = 1e-5f
): ComparisonResult
// from: TensorAssertions.kt:231-236

TensorAssertions.compare(
    expected: GroundTruthTensor,
    actual: GroundTruthTensor,
    atol: Float = ToleranceConfig.STANDARD,
    rtol: Float = 1e-5f
): ComparisonResult
// from: TensorAssertions.kt:251-256
```

`ComparisonResult.success` reports the boolean; the rest of the fields (`maxAbsDiff`, `maxRelDiff`, `mismatchCount`, `firstMismatch*`, `shapesMatch`) feed `toErrorMessage()` for diagnostic output. Use `compare(...)` when a test needs to make a decision based on the diff (e.g. record the worst case across many cases) rather than fail immediately.

## `assertTensorClose(...)` — throwing

```kotlin
TensorAssertions.assertTensorClose(
    expected: GroundTruthTensor,
    actual: Tensor<T, V>,
    atol: Float = ToleranceConfig.STANDARD,
    rtol: Float = 1e-5f,
    message: String? = null
)
// from: TensorAssertions.kt:271-277
```

Throws `AssertionError` with the full diagnostic from `ComparisonResult.toErrorMessage()` (max abs diff, max rel diff, mismatch count, first mismatch index/values). Pass `message` to add a contextual prefix.

## `assertArrayClose(...)` — throwing

```kotlin
TensorAssertions.assertArrayClose(
    expected: FloatArray,
    actual: FloatArray,
    expectedShape: Shape,
    actualShape: Shape,
    atol: Float = ToleranceConfig.STANDARD,
    rtol: Float = 1e-5f,
    message: String? = null
)
// from: TensorAssertions.kt:288-295
```

Use when you already have raw `FloatArray` values (e.g. after `extractFloatData`). Prefer `assertTensorClose` if you have a `Tensor<T, V>` directly.

## `assertShapeEquals(...)` — throwing

```kotlin
TensorAssertions.assertShapeEquals(
    expected: Shape,
    actual: Shape,
    message: String? = null
)
// from: TensorAssertions.kt:307-313
```

Strict equality on `Shape.dimensions`.

## `extractFloatData(...)` — diagnostic helper

```kotlin
TensorAssertions.extractFloatData(tensor: Tensor<T, V>): FloatArray
// from: TensorAssertions.kt:321
```

Pulls a copy of the tensor's contents into a `FloatArray`. Used internally by `assertTensorClose`. Call this directly only when a test must inspect raw values for purposes other than equality (e.g. asserting monotonicity).

## Infix sugar (Kotest-friendly)

```kotlin
public infix fun <T : DType, V> Tensor<T, V>.shouldBeCloseTo(expected: GroundTruthTensor)
// from: TensorAssertions.kt:363-365

public fun <T : DType, V> Tensor<T, V>.shouldBeCloseTo(
    expected: GroundTruthTensor,
    atol: Float,
    rtol: Float = 1e-5f
)
// from: TensorAssertions.kt:370-376
```

The infix overload uses `ToleranceConfig.STANDARD` as `atol`. Use the explicit-argument overload when a non-default tolerance is required — do not call the infix form for `sigmoid` / `softmax` outputs.

## ComparisonResult fields

```kotlin
public data class ComparisonResult(
    val success: Boolean,
    val maxAbsDiff: Float,
    val maxRelDiff: Float,
    val mismatchCount: Int,
    val totalElements: Int,
    val firstMismatchIndex: Int?,
    val firstMismatchExpected: Float?,
    val firstMismatchActual: Float?,
    val shapesMatch: Boolean,
    val expectedShape: Shape,
    val actualShape: Shape
)
// from: TensorAssertions.kt:49-82
```

`matchPercentage` and `toErrorMessage()` are derived helpers on the data class.
