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
2. **Plugins via `alias(libs.plugins.<x>)`.** Direct `id("...") version "..."` is reserved for two cases only: (a) the `sk.ainet.documentation` convention plugin (no version because it's local), (b) plugins in `build-logic/build.gradle.kts` itself.
3. **New module = three edits in one change.** When adding a `skainet-foo` module: (a) create `skainet-foo/build.gradle.kts`, (b) add `include("skainet-foo")` (or the nested form) to `settings.gradle.kts`, (c) register it in `skainet-bom/build.gradle.kts` if it ships as a published artifact.
4. **Dokka comes from the `sk.ainet.dokka` convention plugin.** Modules apply it via `id("sk.ainet.dokka")`, not by configuring Dokka directly. Convention plugins live in `build-logic/convention/src/main/kotlin/`.
5. **`binary-compatibility-validator` is applied on every published module.** Don't suppress it locally; if the API dump changes, regenerate via `./gradlew :module:apiDump` and commit the diff (see `kotlin` skill, api-stability reference).
6. **JVM target = 11 across the project.** Set via `compilerOptions { jvmTarget.set(JvmTarget.JVM_11) }` inside the `android { }` block and inherited elsewhere through KMP defaults. Do not set higher.
7. **No transitive accidents.** Use `api(...)` only when the dependency's types appear in a module's public Kotlin signatures. Default to `implementation(...)`. KSP-generated source goes through `add("kspCommonMainMetadata", project(":skainet-...:...-ksp-processor"))`.

## Workflow — adding a new module

1. Decide the area: pick the right top-level group (`skainet-lang`, `skainet-data`, `skainet-io`, `skainet-backends`, `skainet-compile`, `skainet-models`, `skainet-pipeline`, `skainet-apps`, `skainet-test`).
2. Create the directory and a minimal `build.gradle.kts` that mirrors the closest sibling. Apply the same plugin set (`kotlinMultiplatform`, `vanniktech.mavenPublish`, `binary.compatibility.validator`, `sk.ainet.dokka`, optionally `ksp`, `kotlinx-benchmark`).
3. Add `include("skainet-<group>:<module>")` to `settings.gradle.kts` in the matching `// ====== <GROUP>` section.
4. Add the catalog entry if the module exposes a new external dependency (rare).
5. If the module is published, register it in `skainet-bom/build.gradle.kts`.
6. Run `./gradlew :skainet-<group>:<module>:assemble` to validate the wiring.
7. If a public API was introduced, run `./gradlew :skainet-<group>:<module>:apiDump` and commit the dump.

## Canonical examples

**Module `build.gradle.kts` — KMP library with KSP and Dokka:**

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
// from: SKaiNET/skainet-lang/skainet-lang-core/build.gradle.kts:4-69
```

**Catalog entries — every coordinate routed through `libs.versions.toml`:**

```toml
[versions]
kotlin = "2.3.21"
ksp = "2.3.6"
dokka = "2.1.0"
kotest = "6.1.11"
kover = "0.9.8"
binaryCompatibilityValidator = "0.18.1"

[libraries]
kotlin-test = { module = "org.jetbrains.kotlin:kotlin-test", version.ref = "kotlin" }
kotest-runner-junit5 = { module = "io.kotest:kotest-runner-junit5", version.ref = "kotest" }
kotlinpoet = { module = "com.squareup:kotlinpoet", version.ref = "kotlinpoet" }

[plugins]
kotlinMultiplatform = { id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }
ksp = { id = "com.google.devtools.ksp", version.ref = "ksp" }
skainet-docs = { id = "sk.ainet.documentation" }
// from: SKaiNET/gradle/libs.versions.toml:1-95
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
include("skainet-data:skainet-data-transform")
include("skainet-data:skainet-data-simple")
include("skainet-data:skainet-data-media")

// ====== TEST
include("skainet-test:skainet-test-groundtruth")
include("skainet-test:skainet-test-java")
// from: SKaiNET/settings.gradle.kts:21-73
```

## Related skills

- KMP target list, source-set hierarchy, and `expect`/`actual` placement — see [`../kmp/SKILL.md`](../kmp/SKILL.md).
- Source-code style rules and explicit-API mode — see [`../kotlin/SKILL.md`](../kotlin/SKILL.md).
- Adding the Kotest dependency for a test source set — see [`../skainet-testing/SKILL.md`](../skainet-testing/SKILL.md).

## Anti-patterns

```kotlin
// WRONG — hard-coded coordinate / version
implementation("io.kotest:kotest-runner-junit5:6.1.11")
```
```kotlin
// RIGHT — catalog reference
implementation(libs.kotest.runner.junit5)
```

```kotlin
// WRONG — applying Dokka by id
plugins { id("org.jetbrains.dokka") version "2.1.0" }
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
// RIGHT — also edit settings.gradle.kts AND skainet-bom in the same change
include("skainet-io:skainet-io-newformat") // in settings.gradle.kts
```

## References

- [`references/catalog-aliases.md`](references/catalog-aliases.md) — version, library, and plugin aliases pulled from `libs.versions.toml`.
- [`references/convention-plugins.md`](references/convention-plugins.md) — what `sk.ainet.documentation` / `sk.ainet.dokka` does and how to add a new convention plugin.
