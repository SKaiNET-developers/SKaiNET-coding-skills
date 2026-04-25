---
name: skainet-testing
description: Use ONLY when writing or editing unit tests INSIDE the SKaiNET repository — tests under `SKaiNET/skainet-*/src/commonTest/`, `*/jvmTest/`, or `SKaiNET/skainet-test/skainet-test-java/`. Enforces the in-repo test policy: Kotest spec runner on JVM, `kotlin.test` in commonTest, `TensorAssertions.assertTensorClose` with explicit `ToleranceConfig.{STRICT/STANDARD/RELAXED/GRADIENT}`, Java JUnit 5 in `skainet-test-java`. Trigger tokens include `assertTensorClose`, `assertArrayClose`, `ToleranceConfig`, `GroundTruthTensor`. Do NOT fire on a CONSUMER project writing its own tests against SKaiNET as a dependency — those tests don't have access to `skainet-test-groundtruth` and can use any framework they like.
version: 0.1.0
---

# skainet-testing

Common unit-test strategy across every SKaiNET module: tolerance-aware tensor comparisons, Kotest as the JVM/common runner, JUnit 5 for the Java mirror, fixed source-set placement.

## When to use

- A test under `*/commonTest/`, `*/jvmTest/`, or `skainet-test-java/src/test/` is being added or edited.
- The user mentions Kotest, JUnit, `assertTensorClose`, `ToleranceConfig`, `GroundTruthTensor`, or "compare tensors / floats with tolerance".
- A new module needs its test wiring (which dependencies, which source set, which assertion API).

## When NOT to use

- Building tensors or pipelines for production code — that's `skainet-data-dsl`.
- Building neural networks for production code — that's `skainet-nn-dsl`.
- Editing `build.gradle.kts` to add a Kotest dependency — coordinate with `gradle-multimodule` for the catalog accessor and with `kmp` for the source set.

## Hard rules

1. Compare tensor data ONLY through `sk.ainet.test.groundtruth.TensorAssertions` — never `kotlin.test.assertEquals` on raw tensor data, never `assertArrayEquals` with hardcoded epsilons inside production tests.
2. Every comparison MUST pass an explicit `atol` from `ToleranceConfig` (or call `ToleranceConfig.forOperation(name)`). Bare numeric literals like `1e-5f` MUST NOT appear at the call site.
3. Tolerance picker, no exceptions: `STRICT` (1e-6) for `add` / `subtract` / `multiply` / `divide` / `relu` / `flatten` / `reshape`; `STANDARD` (1e-5) for `matmul` / `conv1d` / `conv2d` / `conv3d` / `sum` / `mean` / `variance`; `RELAXED` (1e-4) for `sigmoid` / `gelu` / `silu` / `softmax` / `logSoftmax` / `leakyRelu`; `GRADIENT` (1e-4) for any backward / autograd assertion; `VERY_RELAXED` (1e-3) only when the operation has documented numerical instability.
4. Kotlin tests live in `commonTest/` whenever they don't reference JVM-only APIs; JVM-only tests live in `jvmTest/`. Java tests live in `skainet-test/skainet-test-java/src/test/java/sk/ainet/java/`.
5. Kotest is the spec runner for JVM-targeted Kotlin tests. Pure `commonTest` (multiplatform) uses `kotlin.test` because Kotest's runner is JVM-only — do not import Kotest from `commonTest` source sets.
6. A new test that compares a SKaiNET tensor against expected values MUST express the expected as a `GroundTruthTensor` (or a `FloatArray` + `Shape`) and call `TensorAssertions.assertTensorClose(...)` / `assertArrayClose(...)`. Never call `tensor.getData().copyToFloatArray()` and then `assertEquals` element by element.

## Workflow

1. Decide the source set:
   - Pure logic (no JVM-only API)? → `commonTest/` with `kotlin.test`.
   - JVM-only fixtures, file IO, or you want Kotest spec syntax? → `jvmTest/` with Kotest.
   - Mirroring a Java consumer surface? → `skainet-test-java/src/test/java/...` with JUnit 5.
2. Pick the tolerance from rule 3 above by looking at the operation under test, not by trial-and-error.
3. Build the expected value once (literal `FloatArray` + `Shape`, or load a `GroundTruthTensor` fixture).
4. Call `TensorAssertions.assertTensorClose(expected, actual, atol = ToleranceConfig.STANDARD)` — pass `rtol` only if the comparison is dominated by relative error (rare; default `1e-5f` is fine for most cases).
5. For shape-only assertions, use `TensorAssertions.assertShapeEquals(expected, actual)`. For Kotest infix style, prefer `actual shouldBeCloseTo expected`.
6. Self-verify before reporting done: every numeric literal in the test that isn't a value being asserted on is gone (no `1e-5f`, `0.001f`, etc. as tolerance arguments — they live in `ToleranceConfig`).

## Canonical examples

**Kotest StringSpec on JVM (preferred for new tests in JVM-only modules):**

```kotlin
import io.kotest.core.spec.style.StringSpec
import sk.ainet.context.DirectCpuExecutionContext
import sk.ainet.lang.tensor.Shape
import sk.ainet.lang.tensor.dsl.tensor
import sk.ainet.lang.types.FP32
import sk.ainet.test.groundtruth.GroundTruthTensor
import sk.ainet.test.groundtruth.TensorAssertions
import sk.ainet.test.groundtruth.ToleranceConfig

class MatmulSpec : StringSpec({
    "2x2 matmul matches expected within STANDARD tolerance" {
        val ctx = DirectCpuExecutionContext.create()
        val a = tensor<FP32, Float>(ctx, FP32::class) {
            tensor { shape(2, 2) { from(1f, 2f, 3f, 4f) } }
        }
        val b = tensor<FP32, Float>(ctx, FP32::class) {
            tensor { shape(2, 2) { from(5f, 6f, 7f, 8f) } }
        }
        val c = a.ops.matmul(a, b)

        val expected = GroundTruthTensor(
            data = floatArrayOf(19f, 22f, 43f, 50f),
            shape = Shape(2, 2)
        )
        TensorAssertions.assertTensorClose(
            expected = expected,
            actual = c,
            atol = ToleranceConfig.STANDARD
        )
    }
})
```

**Multiplatform `commonTest` (no Kotest — `kotlin.test` only):**

```kotlin
import kotlin.test.Test
import sk.ainet.lang.nn.DefaultNeuralNetworkExecutionContext
import sk.ainet.lang.tensor.Shape
import sk.ainet.lang.tensor.dsl.tensor
import sk.ainet.lang.types.FP32
import sk.ainet.test.groundtruth.TensorAssertions
import sk.ainet.test.groundtruth.ToleranceConfig

class SoftmaxCommonTest {
    @Test
    fun `softmax over a 1x4 row sums to 1 within RELAXED tolerance`() {
        val ctx = DefaultNeuralNetworkExecutionContext()
        val x = tensor<FP32, Float>(ctx, FP32::class) {
            tensor { shape(1, 4) { from(1f, 2f, 3f, 4f) } }
        }
        val y = x.ops.softmax(x, dim = -1)
        val sum = y.ops.sum(y, null)

        TensorAssertions.assertArrayClose(
            expected = floatArrayOf(1f),
            actual = floatArrayOf(sum.data.get(0) as Float),
            expectedShape = Shape(1),
            actualShape = sum.shape,
            atol = ToleranceConfig.RELAXED
        )
    }
}
```

**Java JUnit 5 mirror — see [TensorJavaOpsTest.java](../../SKaiNET/skainet-test/skainet-test-java/src/test/java/sk/ainet/java/TensorJavaOpsTest.java):**

```java
@Test
void matmul() {
    Tensor<?, ?> a = SKaiNET.tensor(ctx, new int[]{2, 3}, DType.fp32(),
            new float[]{1f, 2f, 3f, 4f, 5f, 6f});
    Tensor<?, ?> b = SKaiNET.tensor(ctx, new int[]{3, 2}, DType.fp32(),
            new float[]{7f, 8f, 9f, 10f, 11f, 12f});

    Tensor<?, ?> c = TensorJavaOps.matmul(a, b);
    assertArrayEquals(new int[]{2, 2}, c.getShape().getDimensions());

    float[] result = c.getData().copyToFloatArray();
    assertArrayEquals(new float[]{58f, 64f, 139f, 154f}, result, 1e-4f);
}
// from: SKaiNET/skainet-test/skainet-test-java/src/test/java/sk/ainet/java/TensorJavaOpsTest.java:79-93
```

The Java mirror uses raw `assertArrayEquals` with a numeric epsilon because Java consumers don't depend on `skainet-test-groundtruth`. Inside Kotlin tests, `TensorAssertions` is mandatory.

## Related skills

- Test wiring (`testImplementation` lines, Kotest plugin) — see [`../gradle-multimodule/SKILL.md`](../gradle-multimodule/SKILL.md).
- Source-set rules for `commonTest` vs `jvmTest` placement — see [`../kmp/SKILL.md`](../kmp/SKILL.md).
- Java facade convention being tested — see [`../skainet-java-interop/SKILL.md`](../skainet-java-interop/SKILL.md).
- Building the tensors used as inputs in tests — see the `skainet-data-dsl` skill (in the sibling consumer plugin).

## Anti-patterns

```kotlin
// WRONG — bare epsilon at the call site
assertEquals(expected[0], actual.data[0] as Float, 1e-5f)
```
```kotlin
// RIGHT — TensorAssertions + ToleranceConfig
TensorAssertions.assertArrayClose(expected, actualData, expShape, actShape, atol = ToleranceConfig.STANDARD)
```

```kotlin
// WRONG — Kotest imported into commonTest
import io.kotest.core.spec.style.StringSpec  // commonTest cannot run Kotest
```
```kotlin
// RIGHT — kotlin.test for commonTest, Kotest only in jvmTest / src/test
import kotlin.test.Test
```

```kotlin
// WRONG — comparing the wrong tolerance
TensorAssertions.assertTensorClose(expected, sigmoidOut, atol = ToleranceConfig.STRICT)
// sigmoid has accumulated transcendental error
```
```kotlin
// RIGHT — RELAXED for transcendentals
TensorAssertions.assertTensorClose(expected, sigmoidOut, atol = ToleranceConfig.RELAXED)
```

## References

- [`references/tolerance-table.md`](references/tolerance-table.md) — the full operation → tolerance map taken from `ToleranceConfig.forOperation`.
- [`references/assertion-api.md`](references/assertion-api.md) — every public function on `TensorAssertions` and the extension infix sugar, with signatures.
