---
name: kmp
description: Use ONLY when configuring KMP targets, source-set hierarchies, or `expect`/`actual` placement in a module INSIDE the SKaiNET repository. Trigger tokens include `kotlin { ... }`, `iosArm64()`, `commonMain`, `jvmMain`, `expect fun`, `actual fun`, `androidNative`, `wasmJs`, source-set dependency edits in `SKaiNET/skainet-*/build.gradle.kts`. Do NOT fire on KMP setup in a CONSUMER project (an app that depends on SKaiNET) — those concerns are simpler and live in `skainet-consumer-setup`.
version: 0.1.0
---

# kmp

Rules for configuring Kotlin Multiplatform targets and source-set hierarchies in SKaiNET. Pure-logic code lives in `commonMain` and runs on every target; platform-specific implementations are confined to the narrowest source-set that needs them.

## When to use

- Adding a new KMP target to a module (e.g. enabling iosArm64 for a previously JVM-only module).
- Deciding whether a file belongs in `commonMain` / `jvmMain` / a native target / a JS or WASM target.
- Adding `expect` / `actual` declarations.
- Configuring `dependencies { }` blocks per source set.
- Reviewing the KSP-generated source-set layout for a multiplatform module.

## When NOT to use

- Selecting which catalog accessor to use or registering the module — that's `gradle-multimodule`.
- Writing the actual Kotlin code — that's `kotlin`.
- Building Java-facing facades (those always live in `jvmMain`/`sk.ainet.java`) — coordinate with `skainet-java-interop`.

## Hard rules

1. **Canonical target list for a published library** (mirror `skainet-lang-core`'s set unless there's a documented reason not to):
   - `jvm()`
   - `android { namespace = "sk.ainet.<area>"; compileSdk = libs.versions.android.compileSdk.get().toInt(); minSdk = libs.versions.android.minSdk.get().toInt(); compilerOptions { jvmTarget.set(JvmTarget.JVM_11) } }`
   - `iosArm64()`, `iosSimulatorArm64()`
   - `macosArm64()`
   - `linuxX64()`, `linuxArm64()`
   - `androidNativeArm32()`, `androidNativeArm64()` (vendor-native backends)
   - `js { browser() }`
   - `@OptIn(ExperimentalWasmDsl::class) wasmJs { browser() }`, `@OptIn(ExperimentalWasmDsl::class) wasmWasi { nodejs() }`
2. **`expect` lives in `commonMain`. `actual` lives in the narrowest source set that needs the platform API** — `jvmMain` for `java.io`, `iosArm64Main` for an iOS-specific call, etc.
3. **`commonMain` is the default home for Kotlin code.** Move a file out only when it imports a platform API that `commonMain` cannot resolve.
4. **`commonTest` uses `kotlin.test`. `jvmTest` may add Kotest.** Kotest's runner is JVM-only — never import it from a `commonTest` source set.
5. **Source-set dependencies use the per-set DSL** (`commonMain.dependencies { }`, `jvmMain.dependencies { }`), or the `sourceSets { commonMain { dependencies { ... } } }` form. Don't add dependencies to the bare `dependencies { }` block at the top level of a KMP module — that's a JVM-only Gradle pattern.
6. **`api(...)` only when the dependency's types appear in the public Kotlin signatures of the consuming source set.** Otherwise `implementation(...)`. The KSP annotations module is a deliberate `api(...)` because KSP-generated code references those annotations from `commonMain`.
7. **KSP-generated sources for `commonMain` are added explicitly** to `commonMain.kotlin.srcDir("build/generated/ksp/metadata/commonMain/kotlin")`. The `tasks.configureEach { … dependsOn("kspCommonMainKotlinMetadata") }` block at the bottom of the build script is required — copy it verbatim from `skainet-lang-core/build.gradle.kts:72-77` when KSP is involved.
8. **Don't introduce target-specific intermediate source sets without a reason.** Use the default hierarchy template (`iosMain` aggregating `iosArm64Main` + `iosSimulatorArm64Main`; `nativeMain` aggregating all native targets) only when at least two siblings actually share code.

## Workflow

1. Open the closest sibling module's `build.gradle.kts` and copy its target list — divergence from the canonical set MUST be justified in the change description.
2. Decide the source set for the new code:
   - Pure Kotlin, no platform API → `commonMain`.
   - Platform API needed → narrowest source set (`jvmMain`, `iosArm64Main`, `wasmJsMain`).
   - Cross-platform behaviour with platform-specific implementation → `expect` in `commonMain`, `actual` in each platform source set that the module targets.
3. Wire dependencies in the matching source-set block (`commonMain.dependencies { }`, etc.).
4. Add tests in the matching test source set (`commonTest` for cross-target, `jvmTest` for JVM-only tooling like Kotest).
5. Run `./gradlew :module:assemble` to validate every target compiles. If a Native target fails, the source set probably leaked a JVM API — move it to `jvmMain`.

## Canonical examples

**Full target list with explicit-API mode:**

```kotlin
kotlin {
    explicitApi()

    android {
        namespace = "sk.ainet.lang.core"
        compileSdk = libs.versions.android.compileSdk.get().toInt()
        minSdk = libs.versions.android.minSdk.get().toInt()
        compilerOptions {
            jvmTarget.set(JvmTarget.JVM_11)
        }
    }

    iosArm64()
    iosSimulatorArm64()
    macosArm64()
    linuxX64()
    linuxArm64()
    androidNativeArm32()
    androidNativeArm64()

    jvm()

    js {
        browser()
    }

    @OptIn(ExperimentalWasmDsl::class)
    wasmJs {
        browser()
    }

    @OptIn(ExperimentalWasmDsl::class)
    wasmWasi {
        nodejs()
    }
    // ... source sets ...
}
// from: SKaiNET/skainet-lang/skainet-lang-core/build.gradle.kts:14-50
```

**Per-source-set dependencies and KSP-generated source folder:**

```kotlin
sourceSets {
    commonMain {
        kotlin.srcDir("build/generated/ksp/metadata/commonMain/kotlin")
        dependencies {
            api(project(":skainet-lang:skainet-lang-ksp-annotations"))
        }
    }

    jvmMain.dependencies {
        implementation(libs.kotlinx.benchmark.runtime)
    }

    commonTest.dependencies {
        implementation(libs.kotlin.test)
    }
}
// from: SKaiNET/skainet-lang/skainet-lang-core/build.gradle.kts:52-68
```

**KSP wiring required when `commonMain` consumes generated code:**

```kotlin
tasks.configureEach {
    if (name != "kspCommonMainKotlinMetadata" &&
        (name.startsWith("compileKotlin") || name.startsWith("ksp") || name.contains("ourcesJar"))) {
        dependsOn("kspCommonMainKotlinMetadata")
    }
}

dependencies {
    add("kspCommonMainMetadata", project(":skainet-lang:skainet-lang-ksp-processor"))
}
// from: SKaiNET/skainet-lang/skainet-lang-core/build.gradle.kts:72-83
```

## Related skills

- Catalog accessors (`libs.plugins.kotlinMultiplatform`, `libs.kotlinx.io.core`) and module registration — see [`../gradle-multimodule/SKILL.md`](../gradle-multimodule/SKILL.md).
- File-level Kotlin idioms once you've placed a file in the right source set — see [`../kotlin/SKILL.md`](../kotlin/SKILL.md).
- The Java-friendly facade naturally lives in `jvmMain` under `sk/ainet/java/` — see [`../skainet-java-interop/SKILL.md`](../skainet-java-interop/SKILL.md).

## Anti-patterns

```kotlin
// WRONG — top-level dependencies block on a KMP module
dependencies {
    implementation(libs.kotlinx.io.core)
}
```
```kotlin
// RIGHT — per-source-set
sourceSets {
    commonMain.dependencies { implementation(libs.kotlinx.io.core) }
}
```

```kotlin
// WRONG — `actual` in commonMain
// commonMain/.../FileLoader.kt
public actual fun loadModelFile(path: String): ByteArray = TODO()  // commonMain has no platform API
```
```kotlin
// RIGHT — expect in commonMain, actual in jvmMain
// commonMain/.../FileLoader.kt
public expect fun loadModelFile(path: String): ByteArray
// jvmMain/.../FileLoader.kt
public actual fun loadModelFile(path: String): ByteArray = java.io.File(path).readBytes()
```

```kotlin
// WRONG — Kotest in commonTest
// commonTest/.../FooSpec.kt
import io.kotest.core.spec.style.StringSpec  // Kotest runner is JVM-only
```
```kotlin
// RIGHT — Kotest in jvmTest, kotlin.test in commonTest
// commonTest/.../FooTest.kt
import kotlin.test.Test
// jvmTest/.../FooSpec.kt
import io.kotest.core.spec.style.StringSpec
```

## References

- [`references/target-matrix.md`](references/target-matrix.md) — every KMP target SKaiNET ships, what it's used for, and the per-target source-set name.
- [`references/sourceset-rules.md`](references/sourceset-rules.md) — the `commonMain` → platform source-set hierarchy and `expect`/`actual` placement decision tree.
