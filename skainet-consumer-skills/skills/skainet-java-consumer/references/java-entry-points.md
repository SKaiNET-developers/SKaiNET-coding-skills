# Java entry points

The supported Java surface lives in `package sk.ainet.java` and a few matching factory classes elsewhere. Anything not listed here is internal-Kotlin and should NOT be called from Java.

## `SKaiNET` (factory + context)

`@file:JvmName("SKaiNET")` in `SKaiNET/skainet-backends/skainet-backend-cpu/src/jvmMain/kotlin/sk/ainet/java/SKaiNET.kt`.

```java
ExecutionContext ctx = SKaiNET.context();
ExecutionContext train = SKaiNET.context();   // EVAL by default

Tensor<?, ?> t = SKaiNET.tensor(ctx, new int[]{2, 3}, DType.fp32(), new float[]{...});
Tensor<?, ?> ti = SKaiNET.tensorFromInts(ctx, new int[]{2}, DType.int32(), new int[]{1, 2});

Tensor<?, ?> z = SKaiNET.zeros(ctx, new int[]{2, 2});             // dtype defaults to FP32
Tensor<?, ?> z = SKaiNET.zeros(ctx, new int[]{2, 2}, DType.fp16());
Tensor<?, ?> o = SKaiNET.ones(ctx, new int[]{2, 2});
Tensor<?, ?> f = SKaiNET.full(ctx, new int[]{2, 2}, DType.fp32(), 0.5f);
Tensor<?, ?> r = SKaiNET.randn(ctx, new int[]{2, 2});
```

All members are `@JvmStatic` + `@JvmOverloads` — Java sees them as plain static methods with sensible default-omitting overloads.

## `TensorJavaOps` (operations facade)

`@file:JvmName("TensorJavaOps")` in `SKaiNET/skainet-lang/skainet-lang-core/src/jvmMain/kotlin/sk/ainet/java/TensorJavaOps.kt`.

Arithmetic: `add`, `subtract`, `multiply`, `divide`, `addScalar`, `subScalar`, `mulScalar`, `divScalar`.

Linear algebra: `matmul`, `transpose`.

Activations: `relu`, `leakyRelu(a, negativeSlope)` (overload defaults to 0.01), `elu(a, alpha)` (overload defaults to 1.0), `sigmoid`, `silu`, `gelu`, `softmax(a, dim)` (overload defaults to -1), `logSoftmax(a, dim)`.

Reductions: `sum(a, dim)`, `mean(a, dim)`, `variance(a, dim)`. `dim` is nullable (`Integer` from Java) — pass `null` for whole-tensor reduction.

Element-wise math: `sqrt`, `abs`, `sign`, `clamp(a, minVal, maxVal)`.

Shape: `reshape(a, newShape)`, `flatten(a, startDim, endDim)` (defaults 0, -1), `squeeze(a, dim)` (nullable), `unsqueeze(a, dim)`, `narrow(a, dim, start, length)`.

Comparison: `lt(a, value)`, `ge(a, value)`.

Other: `tril(a, k)` (default 0).

All return `Tensor<?, ?>`.

## `StableHloConverterFactory`

`SKaiNET/skainet-compile/skainet-compile-hlo/src/jvmMain/kotlin/...` exposes:

```java
StableHloConverter basic = StableHloConverterFactory.createBasic();
StableHloConverter extended = StableHloConverterFactory.createExtended();
```

Pass a `ComputeGraph` (the lowered form of `dag { }`) to either; the converter emits StableHLO MLIR text.

## `TokenizerFactory`

```java
import sk.ainet.tokenizer.Tokenizer;
import sk.ainet.tokenizer.TokenizerFactory;
import sk.ainet.tokenizer.UnsupportedTokenizerException;

try {
    Tokenizer tok = TokenizerFactory.fromGguf(ggufMetadataMap);
    // also: TokenizerFactory.fromTokenizerJson(...)
} catch (UnsupportedTokenizerException e) { /* ... */ }
```

`fromGguf` reads tokenizer-related keys out of GGUF metadata and constructs a tokenizer if the format is recognised.

## `TensorSpecs` (encoding helper)

`@file:JvmName("TensorSpecs")` exposes:

```java
TensorEncoding enc = TensorSpecs.getTensorEncoding(spec);
TensorSpec annotated = TensorSpecs.withTensorEncoding(spec, TensorEncoding.Q8_0.INSTANCE);
```

Used when you're building a `TensorSpec` for HLO export and need to tag the encoding (Q8_0, TurboQuantPolar, etc.).

## What's NOT supported from Java

- The DSL builders (`tensor { }`, `sequential { }`, `dag { }`) — receiver-typed lambdas don't translate. Build models in a Kotlin module and expose the resulting `Module<FP32, Float>` / `GraphProgram` to Java.
- Suspend functions in `skainet-io-*`. Wrap with a Kotlin shim that returns `CompletableFuture<T>`.
- Internal `*.ops` field on `Tensor<*, *>` — its generics collapse to `?` in Java; use `TensorJavaOps`.
- `KClass<DType>` parameters anywhere — use `DType` instances instead.

## Test-driven verification

The canonical Java usage examples live in `SKaiNET/skainet-test/skainet-test-java/src/test/java/sk/ainet/java/`:

| Test file | What it demonstrates |
|---|---|
| `SKaiNETTest.java` | `SKaiNET.context()`, tensor factories. |
| `TensorJavaOpsTest.java` | Every op exposed by `TensorJavaOps`. |
| `ModelBuilderTest.java` | Building a model from Java via the builder pattern. |
| `ReleaseApiJavaTest.java` | `StableHloConverterFactory`, `TokenizerFactory`, `TensorSpecs`. |

A consumer copying these patterns into their own JUnit 5 tests is the fastest way to validate the dependency set is correct.
