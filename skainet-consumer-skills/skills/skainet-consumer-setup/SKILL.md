---
name: skainet-consumer-setup
description: Use when adding SKaiNET as a library dependency to your Gradle project (KMP, JVM, or Android) — adding `sk.ainet:skainet-bom` to the version catalog, picking which `sk.ainet.core:skainet-*` artifacts the project needs (inference vs. training vs. format-specific I/O), or troubleshooting "I added SKaiNET but X doesn't resolve". Trigger tokens include `sk.ainet:skainet-bom`, `sk.ainet.core:skainet-`, `platform("sk.ainet:skainet-bom")`, `implementation(libs.skainet.*)`, "add SKaiNET to my project". Do NOT fire when editing build scripts INSIDE the SKaiNET repo itself (that's the contributor `gradle-multimodule` skill).
version: 0.1.0
---

# skainet-consumer-setup

Add SKaiNET to a Gradle project that does NOT live inside the SKaiNET repo. Centred on the BOM and the artifact picker so consumers don't end up hand-pinning every transitive version.

## When to use

- Adding SKaiNET to an existing Gradle project for the first time.
- Adding a new `skainet-io-*` or `skainet-data-*` artifact because you discovered you need it (e.g. ONNX support).
- Editing `libs.versions.toml` of a consumer project to register SKaiNET artifacts.
- Switching from a hand-pinned setup to BOM-managed versions.

## When NOT to use

- The user is editing files inside the SKaiNET repo itself (`SKaiNET/build.gradle.kts`, `SKaiNET/settings.gradle.kts`, `SKaiNET/gradle/libs.versions.toml`) — that's the contributor `gradle-multimodule` skill.
- The user is writing application code that uses the DSL — that's `skainet-data-dsl` / `skainet-nn-dsl`.
- The user is wiring an Android-specific backend or asset path — coordinate with `skainet-android-integration`.
- The user is writing a pure-Java consumer — coordinate with `skainet-java-consumer` (the Maven coordinates are similar but the JVM toolchain notes differ).

## Hard rules

1. **Use the BOM.** Add `implementation(platform("sk.ainet:skainet-bom:<VERSION>"))` (or the catalog-accessor equivalent) and depend on `sk.ainet.core:skainet-*` artifacts WITHOUT specifying versions. Hard-pinning per-artifact versions silently lets transitives drift.
2. **The BOM coordinate is `sk.ainet:skainet-bom`. The library coordinates are `sk.ainet.core:skainet-<module>`.** They look like a typo; they're not. The BOM module overrides its group from the project default; libraries publish under `sk.ainet.core`.
3. **At minimum, every consumer needs `skainet-lang-core` + one backend.** `sk.ainet.core:skainet-lang-core` provides the DSL and types; `sk.ainet.core:skainet-backend-cpu` provides the default CPU runtime. Without the backend, `DirectCpuExecutionContext.create()` won't resolve.
4. **Version catalog over inline coordinates.** A consumer project that already uses `gradle/libs.versions.toml` MUST register SKaiNET there too. Mixing styles inside one project is forbidden.
5. **JVM target ≥ 11.** SKaiNET's published `.jar` is compiled for JVM 11. Configuring the consumer below 11 fails at link time.

## Workflow

1. **Pick the version.** Use the latest stable release from <https://github.com/SKaiNET-developers/SKaiNET/releases>. SNAPSHOT (`0.20.0-SNAPSHOT`) only if the consumer explicitly opts in to the snapshot repo.
2. **Add the BOM** to `libs.versions.toml` and to the consuming module(s).
3. **Pick the artifact set** from the picker below (4-7).
4. **Add the snapshot repo** (only if using a `-SNAPSHOT` version) — `maven("https://central.sonatype.com/repository/maven-snapshots/")`.
5. **Verify** by running a one-line forward pass in a test (`./gradlew :app:test`).

## Artifact picker — what do I add?

| You want to … | Add (in addition to `skainet-lang-core` + `skainet-backend-cpu`) |
|---|---|
| Define networks and tensors only (no model files yet) | nothing else |
| Load a GGUF model | `skainet-io-core` + `skainet-io-gguf` |
| Load an ONNX model | `skainet-io-core` + `skainet-io-onnx` |
| Load SafeTensors weights | `skainet-io-core` + `skainet-io-safetensors` |
| Decode images for input pipelines | `skainet-io-image` |
| Use built-in datasets (MNIST, etc.) | `skainet-data-simple` |
| Build preprocessing pipelines (`pipeline().rescale().normalize()`) | `skainet-data-transform` |
| Compile a DAG to StableHLO / C99 | `skainet-compile-core` + `skainet-compile-hlo` (StableHLO) or `skainet-compile-c` |
| Run a higher-level pipeline framework | `skainet-pipeline` |
| Use the YOLO model topology helpers | `skainet-model-yolo` |
| Test with the in-repo assertion library (rare for consumers) | `skainet-test-groundtruth` |

The full BOM-managed artifact list lives in [`references/bom-coordinates.md`](references/bom-coordinates.md).

## Canonical examples

**Kotlin DSL with version catalog (recommended):**

```toml
# gradle/libs.versions.toml (in your consumer project)
[versions]
skainet = "0.20.0-SNAPSHOT"   # or the latest stable

[libraries]
skainet-bom = { module = "sk.ainet:skainet-bom", version.ref = "skainet" }
skainet-lang-core = { module = "sk.ainet.core:skainet-lang-core" }
skainet-backend-cpu = { module = "sk.ainet.core:skainet-backend-cpu" }
skainet-io-gguf = { module = "sk.ainet.core:skainet-io-gguf" }
skainet-data-transform = { module = "sk.ainet.core:skainet-data-transform" }
```

```kotlin
// app/build.gradle.kts
dependencies {
    implementation(platform(libs.skainet.bom))
    implementation(libs.skainet.lang.core)
    implementation(libs.skainet.backend.cpu)
    implementation(libs.skainet.io.gguf)
    implementation(libs.skainet.data.transform)
}
```

**Inline form (acceptable only if the project is already inline-style throughout):**

```kotlin
dependencies {
    implementation(platform("sk.ainet:skainet-bom:0.20.0-SNAPSHOT"))
    implementation("sk.ainet.core:skainet-lang-core")
    implementation("sk.ainet.core:skainet-backend-cpu")
    implementation("sk.ainet.core:skainet-io-gguf")
}
```

**Snapshot repo (only when the version ends in `-SNAPSHOT`):**

```kotlin
// settings.gradle.kts in your consumer project
dependencyResolutionManagement {
    repositories {
        mavenCentral()
        maven("https://central.sonatype.com/repository/maven-snapshots/") {
            content { includeGroupByRegex("sk\\.ainet.*") }
        }
    }
}
```

**KMP consumer adding SKaiNET to common code:**

```kotlin
// app/build.gradle.kts (KMP module)
kotlin {
    jvm()
    androidTarget()
    iosArm64()

    sourceSets {
        commonMain.dependencies {
            implementation(platform(libs.skainet.bom))
            implementation(libs.skainet.lang.core)
        }
        jvmMain.dependencies {
            // Backend is JVM-only by default; for KMP you can use it
            // wherever the JVM (or Android) target compiles.
            implementation(libs.skainet.backend.cpu)
        }
        androidMain.dependencies {
            implementation(libs.skainet.backend.cpu)
        }
    }
}
```

## Related skills

- Building tensors with the DSL once the dependency is in place — [`../skainet-data-dsl/SKILL.md`](../skainet-data-dsl/SKILL.md).
- Building networks with `sequential` / `dag` — [`../skainet-nn-dsl/SKILL.md`](../skainet-nn-dsl/SKILL.md).
- Loading model files — [`../skainet-model-loading/SKILL.md`](../skainet-model-loading/SKILL.md).
- Picking the right `ExecutionContext` for inference — [`../skainet-inference/SKILL.md`](../skainet-inference/SKILL.md).
- Android-specific dependency rules (vendor-native backends, NDK ABIs) — [`../skainet-android-integration/SKILL.md`](../skainet-android-integration/SKILL.md).
- Pure-Java consumer setup (no Kotlin Gradle DSL, Maven users) — [`../skainet-java-consumer/SKILL.md`](../skainet-java-consumer/SKILL.md).

## Anti-patterns

```kotlin
// WRONG — pinning per-artifact versions, no BOM
implementation("sk.ainet.core:skainet-lang-core:0.20.0-SNAPSHOT")
implementation("sk.ainet.core:skainet-io-gguf:0.19.0")  // drift waiting to happen
```
```kotlin
// RIGHT — BOM manages all SKaiNET versions in one place
implementation(platform("sk.ainet:skainet-bom:0.20.0-SNAPSHOT"))
implementation("sk.ainet.core:skainet-lang-core")
implementation("sk.ainet.core:skainet-io-gguf")
```

```kotlin
// WRONG — wrong group for the BOM
implementation(platform("sk.ainet.core:skainet-bom:0.20.0-SNAPSHOT"))
```
```kotlin
// RIGHT — BOM lives at sk.ainet, libraries at sk.ainet.core
implementation(platform("sk.ainet:skainet-bom:0.20.0-SNAPSHOT"))
implementation("sk.ainet.core:skainet-lang-core")
```

```kotlin
// WRONG — only lang-core, no backend
dependencies {
    implementation(platform(libs.skainet.bom))
    implementation(libs.skainet.lang.core)
    // DirectCpuExecutionContext.create() will not resolve
}
```
```kotlin
// RIGHT — pair lang-core with at least one backend
dependencies {
    implementation(platform(libs.skainet.bom))
    implementation(libs.skainet.lang.core)
    implementation(libs.skainet.backend.cpu)
}
```

```kotlin
// WRONG — JVM target below 11
kotlin { jvmToolchain(8) }
```
```kotlin
// RIGHT — JVM 11 minimum
kotlin { jvmToolchain(11) }   // 17 or 21 also fine
```

## References

- [`references/bom-coordinates.md`](references/bom-coordinates.md) — every artifact in `sk.ainet:skainet-bom`, with the consumer-facing `sk.ainet.core:*` Maven coordinate and a one-liner on what each provides.
- [`references/artifact-picker.md`](references/artifact-picker.md) — decision tree for "I need to do X, what artifacts do I add?".
