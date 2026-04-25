# Maven dependencies for Java consumers

Authoritative source: `SKaiNET/skainet-test/skainet-test-java/build.gradle.kts:9-21`. That module is the canonical "what does a Java consumer pull in" example — it's the test harness that exercises the public Java API surface.

## BOM import (Maven)

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
```

After this, declare individual artifacts WITHOUT `<version>`. The BOM constrains them all.

## Required dependencies

```xml
<dependencies>
  <dependency>
    <groupId>sk.ainet.core</groupId>
    <artifactId>skainet-lang-core</artifactId>
  </dependency>
  <dependency>
    <groupId>sk.ainet.core</groupId>
    <artifactId>skainet-backend-cpu</artifactId>
  </dependency>
</dependencies>
```

Both are required for any usable Java consumer:

- `skainet-lang-core` ships `SKaiNET`, `TensorJavaOps`, the `Tensor` type, dtype instances.
- `skainet-backend-cpu` provides `DirectCpuExecutionContext.create()` reachable through `SKaiNET.context()`.

## Optional dependencies (per use case)

```xml
<!-- Model loading (pick the formats you need) -->
<dependency>
  <groupId>sk.ainet.core</groupId>
  <artifactId>skainet-io-core</artifactId>
</dependency>
<dependency>
  <groupId>sk.ainet.core</groupId>
  <artifactId>skainet-io-gguf</artifactId>
</dependency>
<!-- ...skainet-io-onnx, skainet-io-safetensors, skainet-io-image -->

<!-- HLO compilation (StableHloConverterFactory, TokenizerFactory) -->
<dependency>
  <groupId>sk.ainet.core</groupId>
  <artifactId>skainet-compile-core</artifactId>
</dependency>
<dependency>
  <groupId>sk.ainet.core</groupId>
  <artifactId>skainet-compile-hlo</artifactId>
</dependency>

<!-- Built-in datasets (rarely useful for production Java) -->
<dependency>
  <groupId>sk.ainet.core</groupId>
  <artifactId>skainet-data-simple</artifactId>
</dependency>
```

## JDK toolchain

SKaiNET targets JVM 11. Recommended for Java consumers: JDK 21 (matches SKaiNET's own toolchain in `skainet-test-java/build.gradle.kts`).

Maven (`pom.xml`):

```xml
<properties>
  <maven.compiler.source>21</maven.compiler.source>
  <maven.compiler.target>21</maven.compiler.target>
</properties>
```

Or `<release>21</release>` on `maven-compiler-plugin`.

Gradle (Java only, no Kotlin):

```kotlin
java {
    toolchain { languageVersion = JavaLanguageVersion.of(21) }
}
```

## Vector API / preview flags (only if you need them)

The SKaiNET test harness opts into:

```kotlin
tasks.test {
    useJUnitPlatform()
    jvmArgs = listOf("--enable-preview", "--add-modules", "jdk.incubator.vector")
    maxHeapSize = "4g"
}
```

These are required only if your code (a) uses preview Java features, or (b) directly invokes `jdk.incubator.vector`. SKaiNET's CPU backend uses Vector API internally where available; consumers don't need the flag at compile time, but a runtime `--add-modules jdk.incubator.vector` may be required to enable the optimised paths.

## Snapshot repository (if using `-SNAPSHOT`)

```xml
<repositories>
  <repository>
    <id>maven-central-snapshots</id>
    <url>https://central.sonatype.com/repository/maven-snapshots/</url>
    <releases><enabled>false</enabled></releases>
    <snapshots><enabled>true</enabled></snapshots>
  </repository>
</repositories>
```

Skip if using a stable release version.

## Common pitfalls

- **Wrong group on the BOM**: it's `sk.ainet`, not `sk.ainet.core`. Hard rule from `skainet-consumer-setup`.
- **Hard-pinning library versions**: defeats the BOM. Once `<scope>import</scope>` is set up, omit `<version>` on every `sk.ainet.core:*` artifact.
- **JDK 8 toolchain**: SKaiNET's bytecode targets 11. JDK 8 won't link.
- **Missing the snapshot repo for `-SNAPSHOT` versions**: Maven won't synthesize one; declare it explicitly.
