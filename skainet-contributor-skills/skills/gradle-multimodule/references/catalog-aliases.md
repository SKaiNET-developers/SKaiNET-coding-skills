# Version catalog aliases

Authoritative source: `SKaiNET/gradle/libs.versions.toml`. If anything below disagrees, the source wins — update this file.

## Versions

| Alias | Value | Used for |
|---|---|---|
| `kotlin` | 2.3.21 | Kotlin compiler, kotlin-test |
| `ksp` | 2.3.6 | KSP processor + API |
| `dokka` | 2.1.0 | API docs |
| `agp` | 9.2.0 | Android multiplatform library plugin |
| `android-minSdk` | 24 | Android `minSdk` |
| `android-compileSdk` | 36 | Android `compileSdk` |
| `kotlinxCoroutines` | 1.10.2 | Coroutines runtime + test |
| `kotlinxSerializationJson` | 1.11.0 | JSON serialization |
| `kotlinxIo` | 0.9.0 | kotlinx-io-core |
| `kotlinxBenchmark` | 0.4.16 | JVM benchmarks |
| `kotlinxCli` | 0.3.6 | CLI argument parsing (apps) |
| `kotlinpoet` | 2.3.0 | KSP code generation |
| `kctfork` | 0.12.1 | kotlin-compile-testing (KSP tests) |
| `ktorClientCore` | 3.4.3 | Ktor client (model loading from URL) |
| `kotest` | 6.1.11 | Kotest spec runner + assertions |
| `junit` | 4.13.2 | (legacy) JUnit 4 |
| `junitJupiter` | 6.0.3 | JUnit 5 (skainet-test-java) |
| `kover` | 0.9.8 | Coverage |
| `binaryCompatibilityValidator` | 0.18.1 | API surface tracking |
| `pbandk` | 0.16.0 | Protobuf for ONNX |
| `logbackClassic` | 1.5.32 | JVM logging |

## Libraries (most-used aliases)

| Catalog accessor | Maven coordinate |
|---|---|
| `libs.kotlin.test` | `org.jetbrains.kotlin:kotlin-test` |
| `libs.kotlinx.coroutines` | `org.jetbrains.kotlinx:kotlinx-coroutines-core` |
| `libs.kotlinx.coroutines.test` | `org.jetbrains.kotlinx:kotlinx-coroutines-test` |
| `libs.kotlinx.serialization.json` | `org.jetbrains.kotlinx:kotlinx-serialization-json` |
| `libs.kotlinx.io.core` | `org.jetbrains.kotlinx:kotlinx-io-core` |
| `libs.kotlinx.benchmark.runtime` | `org.jetbrains.kotlinx:kotlinx-benchmark-runtime` |
| `libs.kotlinx.cli` | `org.jetbrains.kotlinx:kotlinx-cli` |
| `libs.kotlinpoet` | `com.squareup:kotlinpoet` |
| `libs.kotlinpoet.ksp` | `com.squareup:kotlinpoet-ksp` |
| `libs.ksp.api` | `com.google.devtools.ksp:symbol-processing-api` |
| `libs.kotest.runner.junit5` | `io.kotest:kotest-runner-junit5` |
| `libs.kotest.assertions.core` | `io.kotest:kotest-assertions-core` |
| `libs.kotest.property` | `io.kotest:kotest-property` |
| `libs.junit.jupiter` | `org.junit.jupiter:junit-jupiter` |
| `libs.ktor.client.core` | `io.ktor:ktor-client-core` |
| `libs.pbandk.runtime` | `pro.streem.pbandk:pbandk-runtime` |
| `libs.logback.classic` | `ch.qos.logback:logback-classic` |

## Plugins

| Catalog accessor | Plugin id |
|---|---|
| `libs.plugins.kotlinMultiplatform` | `org.jetbrains.kotlin.multiplatform` |
| `libs.plugins.kotlinSerialization` | `org.jetbrains.kotlin.plugin.serialization` |
| `libs.plugins.jetbrainsKotlinJvm` | `org.jetbrains.kotlin.jvm` |
| `libs.plugins.androidLibrary` | `com.android.library` |
| `libs.plugins.androidMultiplatformLibrary` | `com.android.kotlin.multiplatform.library` |
| `libs.plugins.vanniktech.mavenPublish` | `com.vanniktech.maven.publish` |
| `libs.plugins.kover` | `org.jetbrains.kotlinx.kover` |
| `libs.plugins.binary.compatibility.validator` | `org.jetbrains.kotlinx.binary-compatibility-validator` |
| `libs.plugins.ksp` | `com.google.devtools.ksp` |
| `libs.plugins.dokka` | `org.jetbrains.dokka` |
| `libs.plugins.skainet-docs` | `sk.ainet.documentation` (local convention plugin) |
| `libs.plugins.kotlinx-benchmark` | `org.jetbrains.kotlinx.benchmark` |
| `libs.plugins.shadow` | `com.gradleup.shadow` |
| `libs.plugins.asciidoctorJvm` | `org.asciidoctor.jvm.convert` |
| `libs.plugins.asciidoctorPdf` | `org.asciidoctor.jvm.pdf` |

## Adding a new catalog entry

1. Add a `versions` line if the dependency has a version not yet pinned.
2. Add a `libraries` entry referencing the version: `module = "<group>:<artifact>", version.ref = "<alias>"`.
3. For plugins: add a `plugins` entry. Plugins applied to `build-logic` itself need to be re-declared in `build-logic/settings.gradle.kts` because the composite-build has its own catalog access.
4. Reference from a module's `build.gradle.kts` via `libs.foo.bar` (dashes → dots). Do not paste the coordinate.
