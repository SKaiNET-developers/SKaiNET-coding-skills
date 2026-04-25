---
name: skainet-java-consumer
description: Use when calling SKaiNET from a pure-Java app (Spring Boot, Android Java, Quarkus, plain main()) — adding the JVM-only Maven coordinates, calling `SKaiNET.context()` and `TensorJavaOps.*`, using `StableHloConverterFactory` / `TokenizerFactory`. Trigger tokens include `SKaiNET.context()`, `SKaiNET.tensor(`, `TensorJavaOps.`, `StableHloConverterFactory`, `TokenizerFactory.fromGguf`, `package sk.ainet.java` import in a `.java` file, "from Java", "Java consumer". Do NOT fire when designing the Java facade INSIDE SKaiNET (that's the contributor `skainet-java-interop` skill) or when the consumer is in Kotlin (that's `skainet-inference`).
version: 0.1.0
---

# skainet-java-consumer

Calling SKaiNET from a pure-Java app: which Maven artifacts to depend on, the entry-point classes that were designed to be Java-friendly, idiomatic Java patterns over the `sk.ainet.java` facade.

## When to use

- The consumer project's source is `.java`, not `.kt`, and they want to use SKaiNET.
- Maven (not Gradle) configuration for SKaiNET dependencies.
- Calling `SKaiNET.context()`, `SKaiNET.tensor(...)`, `SKaiNET.zeros(...)`, `TensorJavaOps.add(...)`, etc. from Java.
- Using `StableHloConverterFactory.createBasic()` / `createExtended()` for HLO export.
- Using `TokenizerFactory.fromGguf(metadata)` to build a tokenizer from a GGUF file.
- Reading the Java JUnit 5 tests in `skainet-test-java` as canonical usage examples.

## When NOT to use

- The consumer is writing Kotlin — `skainet-inference` (and the rest of the consumer plugin) covers it more directly.
- The user is editing the SKaiNET facade itself (designing `@JvmStatic` members) — the contributor `skainet-java-interop` skill.
- Android-specific concerns (lifecycle, asset loading) — `skainet-android-integration` (its threading rules apply even from Java; the dispatcher just becomes `ExecutorService`).

## Hard rules

1. **Maven coordinate set for a JVM-only Java consumer:**
   - `sk.ainet:skainet-bom:<VERSION>` (BOM)
   - `sk.ainet.core:skainet-lang-core` (DSL types + `SKaiNET` + `TensorJavaOps`)
   - `sk.ainet.core:skainet-backend-cpu` (`DirectCpuExecutionContext.create()`)
   - Optional loaders: `skainet-io-core` + `skainet-io-{gguf|onnx|safetensors}`
   - Optional HLO: `skainet-compile-core` + `skainet-compile-hlo`
   The `skainet-test-java` consumer module's `build.gradle.kts` is the canonical reference for the dependency set: `SKaiNET/skainet-test/skainet-test-java/build.gradle.kts:9-21`.
2. **JVM target ≥ 11.** Java 21 is recommended (matches SKaiNET's own JDK toolchain). The HLO test harness uses preview features and the Vector API (`--enable-preview --add-modules jdk.incubator.vector`); only enable those flags if you actually use Vector / preview APIs.
3. **Always go through `SKaiNET` and `TensorJavaOps` — never import internal `sk.ainet.lang.*` or `sk.ainet.context.*` packages from Java unless absolutely necessary.** The Java entry points are the supported surface.
4. **Tensors crossing into Java are `Tensor<?, ?>`** (the Java view of `Tensor<*, *>`). Don't try to declare `Tensor<DType, Float>` in Java — the Kotlin `*` projection collapses to `?` and any further generic bounds are awkward.
5. **DType is `DType.fp32()`, `DType.int32()`, `DType.int8()`, etc.** — never `KClass`. The `SKaiNET` factory takes a `DType` instance and resolves to a `KClass<DType>` internally.
6. **Don't call suspend Kotlin APIs from Java directly.** If a SKaiNET function in `kotlin/sk/ainet/io/...` is `suspend`, Java sees an extra `Continuation` parameter — that's not supportable from a normal Java caller. Use a Kotlin shim that exposes `CompletableFuture<T>` or a blocking helper.

## Workflow

1. Add the Maven dependencies (Maven `<dependency>` blocks or Gradle if Java + Gradle is the setup).
2. Bootstrap an `ExecutionContext`: `ExecutionContext ctx = SKaiNET.context();`.
3. Build input tensors via `SKaiNET.tensor(...)` / `SKaiNET.zeros(...)` / `SKaiNET.full(...)`.
4. Call ops via `TensorJavaOps.<op>(...)` — never reach into the Kotlin `*.ops` field directly.
5. For HLO export / tokenisation, use `StableHloConverterFactory` and `TokenizerFactory`.

## Canonical examples

**Maven `pom.xml` (JVM-only Java consumer):**

```xml
<dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>sk.ainet</groupId>
      <artifactId>skainet-bom</artifactId>
      <version>0.20.0-SNAPSHOT</version>
      <type>pom</type>
      <scope>import</scope>
    </dependency>
  </dependencies>
</dependencyManagement>

<dependencies>
  <dependency>
    <groupId>sk.ainet.core</groupId>
    <artifactId>skainet-lang-core</artifactId>
  </dependency>
  <dependency>
    <groupId>sk.ainet.core</groupId>
    <artifactId>skainet-backend-cpu</artifactId>
  </dependency>
  <!-- optional: loaders -->
  <dependency>
    <groupId>sk.ainet.core</groupId>
    <artifactId>skainet-io-core</artifactId>
  </dependency>
  <dependency>
    <groupId>sk.ainet.core</groupId>
    <artifactId>skainet-io-gguf</artifactId>
  </dependency>
</dependencies>
```

**Gradle (Java + Gradle, no Kotlin):**

```kotlin
dependencies {
    implementation(platform("sk.ainet:skainet-bom:0.20.0-SNAPSHOT"))
    implementation("sk.ainet.core:skainet-lang-core")
    implementation("sk.ainet.core:skainet-backend-cpu")
}

java {
    toolchain { languageVersion = JavaLanguageVersion.of(21) }
}
```

**Java tensor ops — minimal arithmetic:**

```java
package com.example;

import sk.ainet.context.ExecutionContext;
import sk.ainet.java.SKaiNET;
import sk.ainet.java.TensorJavaOps;
import sk.ainet.lang.tensor.Tensor;
import sk.ainet.lang.types.DType;

public class TensorAddDemo {
    public static void main(String[] args) {
        ExecutionContext ctx = SKaiNET.context();

        Tensor<?, ?> a = SKaiNET.tensor(ctx, new int[]{2, 2}, DType.fp32(),
                new float[]{1f, 2f, 3f, 4f});
        Tensor<?, ?> b = SKaiNET.tensor(ctx, new int[]{2, 2}, DType.fp32(),
                new float[]{10f, 20f, 30f, 40f});

        Tensor<?, ?> c = TensorJavaOps.add(a, b);
        float[] result = c.getData().copyToFloatArray();
        for (float v : result) {
            System.out.println(v);
        }
    }
}
// from: SKaiNET/skainet-test/skainet-test-java/src/test/java/sk/ainet/java/TensorJavaOpsTest.java:25-38
```

**Default-argument overloads (`@JvmOverloads` from Kotlin gives you these for free):**

```java
// Both work — pick the shape that suits the call site
Tensor<?, ?> z3 = SKaiNET.zeros(ctx, new int[]{2, 2}, DType.fp32());
Tensor<?, ?> z2 = SKaiNET.zeros(ctx, new int[]{2, 2});         // dtype defaults to FP32

Tensor<?, ?> r1 = TensorJavaOps.softmax(input);                 // dim defaults to -1
Tensor<?, ?> r2 = TensorJavaOps.softmax(input, -1);
```

**Activation chain:**

```java
Tensor<?, ?> logits = TensorJavaOps.matmul(x, w);
Tensor<?, ?> hidden = TensorJavaOps.relu(logits);
Tensor<?, ?> out = TensorJavaOps.softmax(hidden, -1);
```

**HLO export (Java consumer of `skainet-compile-hlo`):**

```java
import sk.ainet.compile.hlo.StableHloConverter;
import sk.ainet.compile.hlo.StableHloConverterFactory;

StableHloConverter basic = StableHloConverterFactory.createBasic();
StableHloConverter extended = StableHloConverterFactory.createExtended();
// hand a ComputeGraph to one of these to produce StableHLO MLIR text
// from: SKaiNET/skainet-test/skainet-test-java/src/test/java/sk/ainet/java/ReleaseApiJavaTest.java
```

**Tokenizer from GGUF metadata:**

```java
import sk.ainet.tokenizer.Tokenizer;
import sk.ainet.tokenizer.TokenizerFactory;
import sk.ainet.tokenizer.UnsupportedTokenizerException;

try {
    Tokenizer tok = TokenizerFactory.fromGguf(ggufMetadataMap);
    int[] ids = tok.encode("Hello SKaiNET");
} catch (UnsupportedTokenizerException e) {
    // GGUF didn't carry a recognised tokenizer; fall back to a manual one
}
// from: SKaiNET/skainet-test/skainet-test-java/src/test/java/sk/ainet/java/ReleaseApiJavaTest.java
```

**Spring Boot bean wiring (typical):**

```java
@Configuration
public class SkainetConfig {

    @Bean(destroyMethod = "")
    public ExecutionContext skainetExecutionContext() {
        return SKaiNET.context();
    }
}

@Service
public class Classifier {
    private final ExecutionContext ctx;

    public Classifier(ExecutionContext ctx) { this.ctx = ctx; }

    public float[] classify(float[] features) {
        Tensor<?, ?> x = SKaiNET.tensor(ctx, new int[]{1, features.length}, DType.fp32(), features);
        Tensor<?, ?> y = TensorJavaOps.softmax(model.forward(x, ctx), -1);  // model is Kotlin-built and exposed
        return y.getData().copyToFloatArray();
    }
}
```

For models, consumers typically build the `Module` in a small Kotlin module (the DSL is awkward from Java) and expose the `Module<FP32, Float>` to the Java service layer. Mixed-language consumer projects are the norm.

## Related skills

- The Maven / Gradle dependency picker — [`../skainet-consumer-setup/SKILL.md`](../skainet-consumer-setup/SKILL.md).
- Loading a model from Java (loaders are `suspend` in Kotlin — needs a Kotlin shim) — [`../skainet-model-loading/SKILL.md`](../skainet-model-loading/SKILL.md).
- The forward pass and threading rules (apply with `ExecutorService` instead of coroutines) — [`../skainet-inference/SKILL.md`](../skainet-inference/SKILL.md).
- Designing the facade itself (contributor side) — see the contributor `skainet-java-interop` skill.

## Anti-patterns

```java
// WRONG — KClass parameter from Java
SKaiNET.tensor(ctx, new int[]{2, 2}, FP32.class, data);   // FP32::class.java is awkward
```
```java
// RIGHT — DType instance
SKaiNET.tensor(ctx, new int[]{2, 2}, DType.fp32(), data);
```

```java
// WRONG — calling Kotlin properties as fields
Tensor<?, ?> a = ...;
int[] dims = a.shape.dimensions;   // Tensor.getShape() is the Java view
```
```java
// RIGHT — Java-style accessors
int[] dims = a.getShape().getDimensions();
```

```java
// WRONG — reaching into the Kotlin ops object
Tensor<?, ?> sum = a.getOps().add(a, b);   // ops is Tensor<DType, Any?>.ops — generic chaos in Java
```
```java
// RIGHT — go through the facade
Tensor<?, ?> sum = TensorJavaOps.add(a, b);
```

```java
// WRONG — calling a suspend function directly
Tensor<?, ?> loaded = ggufReader.loadTensor("name");   // compiles only via Continuation; runtime mess
```
```java
// RIGHT — write a Kotlin shim that exposes a CompletableFuture or blocking helper
public CompletableFuture<Tensor<?, ?>> loadTensorAsync(String name) {
    return GlobalScope.future { ggufReader.loadTensor(name) }
}
```

```java
// WRONG — JVM 8 toolchain
java { toolchain { languageVersion = JavaLanguageVersion.of(8) } }
```
```java
// RIGHT — JVM 11+
java { toolchain { languageVersion = JavaLanguageVersion.of(21) } }
```

## References

- [`references/maven-deps.md`](references/maven-deps.md) — Maven `<dependency>` blocks, BOM import scope, JDK toolchain notes.
- [`references/java-entry-points.md`](references/java-entry-points.md) — every Java-friendly entry point currently shipped (`SKaiNET`, `TensorJavaOps`, `StableHloConverterFactory`, `TokenizerFactory`, `TensorSpecs`).
