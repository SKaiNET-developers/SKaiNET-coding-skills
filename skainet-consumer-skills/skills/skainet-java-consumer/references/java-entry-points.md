# Java entry points

The supported Java surface lives in `package sk.ainet.java` and a few matching factory classes elsewhere. Anything not listed here is internal-Kotlin and should NOT be called from Java.

## `SKaiNET` (factory + context)

`object SKaiNET` (`@file:JvmName("SKaiNET")`) in `SKaiNET/skainet-backends/skainet-backend-cpu/src/jvmMain/kotlin/sk/ainet/java/SKaiNET.kt`.

```java
ExecutionContext ctx = SKaiNET.context();     // CPU context, EVAL phase

Tensor<?, ?> t = SKaiNET.tensor(ctx, new int[]{2, 3}, DType.fp32(), new float[]{...});
Tensor<?, ?> ti = SKaiNET.tensorFromInts(ctx, new int[]{2}, DType.int32(), new int[]{1, 2});

Tensor<?, ?> z = SKaiNET.zeros(ctx, new int[]{2, 2});             // dtype defaults to FP32
Tensor<?, ?> z = SKaiNET.zeros(ctx, new int[]{2, 2}, DType.fp16());
Tensor<?, ?> o = SKaiNET.ones(ctx, new int[]{2, 2});
Tensor<?, ?> f = SKaiNET.full(ctx, new int[]{2, 2}, DType.fp32(), 0.5f);
Tensor<?, ?> r = SKaiNET.randn(ctx, new int[]{2, 2});
```

All members are `@JvmStatic`; `zeros` / `ones` / `randn` are also `@JvmOverloads` (dtype defaults to FP32). For a training-phase context, call `DirectCpuExecutionContext.create(Phase.TRAIN)` directly — it is `@JvmStatic @JvmOverloads` too (defaults to `Phase.EVAL`).

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

## Model building + training facade (`sk.ainet.java`, in `skainet-lang-core`)

All four live in `skainet-lang-core`'s `src/jvmMain/kotlin/sk/ainet/java/`:

- **`SequentialModelBuilder`** — fluent builder for feed-forward stacks: `new SequentialModelBuilder(ctx)` (optional second `DType` arg, defaults FP32), then `.input(n)`, `.dense(n)`, `.relu()`, `.sigmoid()`, `.silu()`, `.gelu()`, `.softmax(dim)` (default -1), `.flatten(startDim, endDim)` (defaults 1, -1), `.build()` → `Module`.
- **`Optimizers`** — `@JvmStatic @JvmOverloads` factories: `adam(lr, beta1, beta2, epsilon, weightDecay)` (defaults 0.001/0.9/0.999/1e-8/0.0), `adamw(...)` (weightDecay defaults 0.01, decoupled), `sgd(lr, momentum, weightDecay)`.
- **`Losses`** — `crossEntropy(dim)`, `categoricalCrossEntropy(dim)`, `sparseCategoricalCrossEntropy(dim)`, `mse()`, `mae()`, `binaryCrossEntropy(epsilon)`, `bceWithLogits()`, `huber(delta)`, `hinge(margin)`, `squaredHinge(margin)`, `poisson(logInput, epsilon)`.
- **`TrainingLoop`** — `TrainingLoop.builder().model(m).loss(l).optimizer(o).context(ctx).build()`; then `step(x, y)` → float loss, `train(Supplier<Iterator<Pair<Tensor, Tensor>>>, epochs)` → `TrainingResult`, or `trainAsync(...)` → `CompletableFuture<TrainingResult>` (virtual threads).

## `StableHloConverterFactory`

`object StableHloConverterFactory` in `SKaiNET/skainet-compile/skainet-compile-hlo/src/commonMain/kotlin/sk/ainet/compile/hlo/StableHloConverterFactory.kt` (common code now, no longer a jvmMain-only file):

```java
StableHloConverter basic = StableHloConverterFactory.createBasic();
StableHloConverter extended = StableHloConverterFactory.createExtended();
StableHloConverter fast = StableHloConverterFactory.createFast();
```

All three are `@JvmStatic @JvmOverloads`; the no-arg forms shown above work from Java, and optional parameters (`ConstantMaterializationPolicy`, `ConversionErrorPolicy`, …) can be passed positionally. Pass a `ComputeGraph` (the lowered form of `dag { }`) to a converter; it emits StableHLO MLIR text.

## `TokenizerFactory`

Package **`sk.ainet.io.tokenizer`** (moved from `sk.ainet.tokenizer`), shipped in `skainet-io-core`:

```java
import sk.ainet.io.tokenizer.Tokenizer;
import sk.ainet.io.tokenizer.TokenizerFactory;
import sk.ainet.io.tokenizer.UnsupportedTokenizerException;

try {
    Tokenizer tok = TokenizerFactory.fromGguf(ggufFieldsMap);     // Map<String, Object>
    // also: TokenizerFactory.fromTokenizerJson(jsonString)
} catch (UnsupportedTokenizerException e) { /* ... */ }
```

Dispatch is per-architecture, not per file format: `fromGguf` inspects `tokenizer.ggml.model`, `fromTokenizerJson` inspects `model.type`. Byte-level BPE (Qwen, GPT-2, Mistral-Nemo) and SentencePiece (LLaMA, Gemma, TinyLlama) are supported; WordPiece/BERT throws `UnsupportedTokenizerException`.

## `TensorSpecs` (encoding helper)

`@file:JvmName("TensorSpecs")` on `skainet-lang-core`'s `sk/ainet/lang/tensor/ops/TensorSpecEncoding.kt` exposes:

```java
TensorEncoding enc = TensorSpecs.getTensorEncoding(spec);
TensorSpec annotated = TensorSpecs.withTensorEncoding(spec, TensorEncoding.Q8_0.INSTANCE);
```

Used when you're building a `TensorSpec` for HLO export and need to tag the encoding (Q8_0, etc.). `withTensorEncoding` returns a copy; `getTensorEncoding` returns `null` on an un-annotated spec.

## What's NOT supported from Java

- The DSL builders (`tensor { }`, `sequential { }`, `dag { }`) — receiver-typed lambdas don't translate. Simple feed-forward stacks can be built with `SequentialModelBuilder`; for everything else build models in a Kotlin module and expose the resulting `Module<FP32, Float>` / `GraphProgram` to Java.
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
