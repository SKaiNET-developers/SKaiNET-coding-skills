---
name: gradle-multimodule
description: Use ONLY when editing build scripts INSIDE the SKaiNET repository — `SKaiNET/build.gradle.kts`, `SKaiNET/settings.gradle.kts`, `SKaiNET/gradle/libs.versions.toml`, anything under `SKaiNET/build-logic/`, or adding/renaming/removing a `skainet-*` module within SKaiNET. Enforces version-catalog-only references, convention-plugin reuse, BOM registration, binary-compatibility-validator, vanniktech maven-publish, kover. Do NOT fire on a CONSUMER project's build script that just depends on `sk.ainet:skainet-bom` — that's the `skainet-consumer-setup` skill.
version: 0.1.0
---

# gradle-multimodule

Rules for editing the SKaiNET multi-module Gradle build. The project is a Gradle composite build: `build-logic/` is included via `includeBuild` and contributes convention plugins; every module under `skainet-*/` is included from `settings.gradle.kts`; all dependency coordinates resolve through `gradle/libs.versions.toml`.

## When to use

- Adding, renaming, or removing a Gradle module.
- Editing any `build.gradle.kts`, `settings.gradle.kts`, or `*.gradle.kts` under `build-logic/`.
- Editing `gradle/libs.versions.toml` (versions, libraries, plugins, bundles).
- Wiring a new dependency into a module.
- Adjusting publication, BOM membership, or coverage configuration.

## When NOT to use

- Selecting which Kotlin source-set a file belongs in or which KMP target a module supports — that's `kmp`.
- Writing the actual production Kotlin code — that's `kotlin`.
- Test wiring beyond adding the dependency line — `skainet-testing` owns assertion APIs and source-set placement for tests.

## Hard rules

1. **Version-catalog-only.** Every dependency, plugin, and version reference in any `build.gradle.kts` MUST go through `libs.versions.<x>`, `libs.<library>`, or `libs.plugins.<plugin>`. Hard-coded version strings (`"1.10.2"`, `version = "2.3.21"`) MUST NOT appear in module build scripts.
2. **Plugins via `alias(libs.plugins.<x>)`.** Direct `id("...")` without a version is the pattern for the in-tree convention plugins (`sk.ainet.dokka`, `sk.ainet.multiplatform`, `sk.ainet.documentation`, `sk.ainet.npm-pins`, `sk.ainet.maven-pins`, `sk.ainet.transformers.bom-coverage`) — local plugins have no version to track. `id("...") version "..."` with a literal version is reserved for `build-logic/convention/build.gradle.kts` itself.
3. **New published module = four edits in one change.** When adding a `skainet-foo` module: (a) create `skainet-foo/build.gradle.kts`, (b) add `include("skainet-foo")` (or the nested form) to `settings.gradle.kts`, (c) add the module's own `gradle.properties` with `POM_ARTIFACT_ID` and `POM_NAME` — without it the publication has no POM name and never reaches Maven Central (this bit `skainet-compile-minerva` once), (d) apply `alias(libs.plugins.vanniktech.mavenPublish)`. BOM membership is automatic: the `sk.ainet.transformers.bom-coverage` plugin on `skainet-bom` adds every sibling that applies the publish plugin as an `api` constraint; to keep a published module OUT of the BOM, add its path to `bomCoverage.excludePublished` in `skainet-bom/build.gradle.kts`.
4. **Dokka comes from the `sk.ainet.dokka` convention plugin.** Modules apply it via `id("sk.ainet.dokka")`, not by configuring Dokka directly. Convention plugins live in `build-logic/convention/src/main/kotlin/`.
5. **`binary-compatibility-validator` is applied on every published module.** Don't suppress it locally; if the API dump changes, regenerate via `./gradlew :module:apiDump` and commit the diff (see `kotlin` skill, api-stability reference).
6. **JDK 21+, Java 21 bytecode on JVM, JVM 11 on Android.** The root `build.gradle.kts` requires JDK 21+, sets `JvmTarget.JVM_21` on every Kotlin JVM target and `options.release = 21` for Java sources — do not re-declare that per module. Android compilations are the exception: they target `JvmTarget.JVM_11` (set in the `android { }` block, or via `skainet { androidJvmTarget }` under the `sk.ainet.multiplatform` plugin; the `skainet-io` family explicitly ships `JVM_1_8`).
7. **No transitive accidents.** Use `api(...)` only when the dependency's types appear in a module's public Kotlin signatures. Default to `implementation(...)`. KSP-generated source goes through `add("kspCommonMainMetadata", project(":skainet-...:...-ksp-processor"))`.

## Workflow — adding a new module

1. Decide the area: pick the right top-level group (`skainet-lang`, `skainet-data`, `skainet-io`, `skainet-backends`, `skainet-compile`, `skainet-models`, `skainet-pipeline`, `skainet-apps`, `skainet-test`).
2. Create the directory and a minimal `build.gradle.kts` that mirrors the closest sibling. Prefer the convention-plugin set (`id("sk.ainet.multiplatform")`, `androidMultiplatformLibrary` for Android, `vanniktech.mavenPublish`, `binary.compatibility.validator`, `sk.ainet.dokka`, optionally `ksp`, `kotlinx-benchmark`) plus a `skainet { namespace = "..." }` block.
3. Add `include("skainet-<group>:<module>")` to `settings.gradle.kts` in the matching `// ====== <GROUP>` section.
4. Add the module's `gradle.properties` with `POM_ARTIFACT_ID` / `POM_NAME` (published modules), and `skainet.targets=` only when diverging from the default target set.
5. Add the catalog entry if the module exposes a new external dependency (rare). The BOM picks the module up automatically once `vanniktech.mavenPublish` is applied.
6. Run `./gradlew :skainet-<group>:<module>:assemble` to validate the wiring.
7. If a public API was introduced, run `./gradlew :skainet-<group>:<module>:apiDump` and commit the dump.

## Canonical examples

**Module `build.gradle.kts` — convention-plugin form (preferred for new modules):**

```kotlin
plugins {
    id("sk.ainet.multiplatform")
    alias(libs.plugins.androidMultiplatformLibrary)
    alias(libs.plugins.vanniktech.mavenPublish)
    alias(libs.plugins.binary.compatibility.validator)
    id("sk.ainet.dokka")
}

// Targets, explicitApi() and kotlin-test in commonTest come from sk.ainet.multiplatform.
skainet {
    namespace = "sk.ainet.pipeline"
}
// from: SKaiNET/skainet-pipeline/build.gradle.kts:1-15
```

**Module `build.gradle.kts` — hand-rolled KMP library with KSP and Dokka (older modules):**

```kotlin
plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidMultiplatformLibrary)
    alias(libs.plugins.vanniktech.mavenPublish)
    alias(libs.plugins.binary.compatibility.validator)
    alias(libs.plugins.ksp)
    id("sk.ainet.dokka")
    id("org.jetbrains.kotlinx.benchmark")
}

kotlin {
    explicitApi()
    // ... target list goes here — see kmp skill ...

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
}
// from: SKaiNET/skainet-lang/skainet-lang-core/build.gradle.kts:4-82
```

**Catalog entries — every coordinate routed through `libs.versions.toml`:**

```toml
[versions]
kotlin = "2.4.20"
ksp = "2.3.10"
dokka = "2.2.0"
kotest = "6.2.5"
kover = "0.9.9"
binaryCompatibilityValidator = "0.18.2"

[libraries]
kotlin-test = { module = "org.jetbrains.kotlin:kotlin-test", version.ref = "kotlin" }
kotest-runner-junit5 = { module = "io.kotest:kotest-runner-junit5", version.ref = "kotest" }
kotlinpoet = { module = "com.squareup:kotlinpoet", version.ref = "kotlinpoet" }

[plugins]
kotlinMultiplatform = { id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }
ksp = { id = "com.google.devtools.ksp", version.ref = "ksp" }
skainet-docs = { id = "sk.ainet.documentation" }
skainet-multiplatform = { id = "sk.ainet.multiplatform" }
skainet-npmPins = { id = "sk.ainet.npm-pins" }
// excerpt — values drift; SKaiNET/gradle/libs.versions.toml is the source of truth
// (it also holds the npm security pins forced into the kotlin-js-store lockfiles)
```

**`settings.gradle.kts` — module registration, grouped by area:**

```kotlin
includeBuild("build-logic")

// ====== LANG
include("skainet-lang:skainet-lang-core")
include("skainet-lang:skainet-lang-models")
include("skainet-lang:skainet-lang-ksp-annotations")
include("skainet-lang:skainet-lang-ksp-processor")
include("skainet-lang:skainet-lang-dag")

// ====== DATA
include("skainet-data:skainet-data-api")
include("skainet-data:skainet-data-source")
include("skainet-data:skainet-data-transform")
include("skainet-data:skainet-data-simple")
include("skainet-data:skainet-data-media")

// ====== TEST
include("skainet-test:skainet-test-groundtruth")
include("skainet-test:skainet-test-java")
// from: SKaiNET/settings.gradle.kts:21-78 (abridged — the full file also includes the
// COMPILE, BACKENDS, BENCHMARKS, PIPELINE, IO, models, BOM, APPS and DOCS sections)
```

## Related skills

- KMP target list, source-set hierarchy, and `expect`/`actual` placement — see [`../kmp/SKILL.md`](../kmp/SKILL.md).
- Source-code style rules and explicit-API mode — see [`../kotlin/SKILL.md`](../kotlin/SKILL.md).
- Adding the Kotest dependency for a test source set — see [`../skainet-testing/SKILL.md`](../skainet-testing/SKILL.md).

## Anti-patterns

```kotlin
// WRONG — hard-coded coordinate / version
implementation("io.kotest:kotest-runner-junit5:6.2.5")
```
```kotlin
// RIGHT — catalog reference
implementation(libs.kotest.runner.junit5)
```

```kotlin
// WRONG — applying Dokka by id
plugins { id("org.jetbrains.dokka") version "2.2.0" }
```
```kotlin
// RIGHT — apply the convention plugin (it configures Dokka)
plugins { id("sk.ainet.dokka") }
```

```kotlin
// WRONG — adding a new module without registering it
// (skainet-io/skainet-io-newformat/build.gradle.kts created, but settings.gradle.kts unchanged)
```
```kotlin
// RIGHT — also edit settings.gradle.kts AND add the module's gradle.properties
// (POM_ARTIFACT_ID / POM_NAME) in the same change; the BOM picks it up automatically
include("skainet-io:skainet-io-newformat") // in settings.gradle.kts
```

## References

- [`references/catalog-aliases.md`](references/catalog-aliases.md) — version, library, and plugin aliases pulled from `libs.versions.toml`.
- [`references/convention-plugins.md`](references/convention-plugins.md) — the full `sk.ainet.*` convention-plugin set (`multiplatform`, `dokka`, `documentation`, `npm-pins`, `maven-pins`, `bom-coverage`) and how to add a new one.
