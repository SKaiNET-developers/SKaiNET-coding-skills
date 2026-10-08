# Version catalog aliases

Authoritative source: `SKaiNET/gradle/libs.versions.toml`. **Always read the toml for the
current pin** — the values drift every release; the alias names below are the durable part.
Snapshot values noted here were verified against 0.57.0 (Kotlin 2.4.20, AGP 9.4.1,
Ktor 3.6.0, kotest 6.2.5, KSP 2.3.10, Dokka 2.2.0, kotlinx-benchmark 0.5.0,
binary-compatibility-validator 0.18.2, kover 0.9.9).

## Versions

| Alias | Used for |
|---|---|
| `kotlin` | Kotlin compiler, kotlin-test, KGP (2.4.20 as of 0.57.0) |
| `ksp` | KSP processor + API |
| `dokka` | API docs (Dokka 2.x) |
| `agp` | Android Gradle plugin / android multiplatform library plugin (9.4.1 as of 0.57.0) |
| `android-minSdk` / `android-compileSdk` | Android `minSdk` (24) / `compileSdk` (36) |
| `android-ndk` | Pinned NDK for `skainet-backend-jni-cpu`'s externalNativeBuild (r28+: 16 KB-page-aligned .so's) |
| `kotlinxCoroutines` | Coroutines runtime + test |
| `kotlinxSerializationJson` | JSON serialization |
| `kotlinxIo` | kotlinx-io-core |
| `kotlinxBenchmark` | JVM benchmarks |
| `kotlinxCli` | CLI argument parsing (apps) |
| `kotlinBrowser` | kotlinx-browser (wasm/js) |
| `kotlinpoet` | KSP code generation |
| `kctfork` | kotlin-compile-testing (KSP tests) |
| `ktorClientCore` / `ktorClientPlugins` | Ktor client (model loading from URL) |
| `kotest` | Kotest runner + assertions + property (used in `skainet-apps` test suites) |
| `junit` | (legacy) JUnit 4 |
| `junitJupiter` | JUnit 5 (skainet-test-java) |
| `kover` | Coverage |
| `binaryCompatibilityValidator` | API surface tracking |
| `pbandk` | Protobuf for ONNX |
| `logbackClassic` | JVM logging |
| `jacksonDatabind`, `jsonSchemaValidator`, `jsonSchemaValidatorVersion` | JSON schema validation (build-logic / docs pipeline) |
| `npm-*` | npm security pins forced into the `kotlin-js-store` lockfiles via the `sk.ainet.npm-pins` root plugin (`skainet { npmPins { pin(...) } }`); never edit `kotlin-js-store/**/yarn.lock` by hand |

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
| `libs.kotlin.compile.testing` / `.ksp` | `dev.zacsweers.kctfork:core` / `:ksp` |
| `libs.kotest.runner.junit5` | `io.kotest:kotest-runner-junit5` |
| `libs.kotest.assertions.core` | `io.kotest:kotest-assertions-core` |
| `libs.kotest.property` | `io.kotest:kotest-property` |
| `libs.junit.jupiter` | `org.junit.jupiter:junit-jupiter` |
| `libs.junit.platform.launcher` | `org.junit.platform:junit-platform-launcher` |
| `libs.ktor.client.core` (+ `.cio`, `.darwin`, `.js`, `.android`, …) | `io.ktor:ktor-client-*` |
| `libs.pbandk.runtime` | `pro.streem.pbandk:pbandk-runtime` |
| `libs.logback.classic` | `ch.qos.logback:logback-classic` |
| `libs.kotlin.gradlePlugin` / `libs.android.gradlePlugin` | KGP / AGP types — `compileOnly` in build-logic only |

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
| `libs.plugins.skainet-multiplatform` | `sk.ainet.multiplatform` (local convention plugin) |
| `libs.plugins.skainet-npmPins` | `sk.ainet.npm-pins` (local, root project only) |
| `libs.plugins.skainet-mavenPins` | `sk.ainet.maven-pins` (local, root project only) |
| `libs.plugins.kotlinx-benchmark` | `org.jetbrains.kotlinx.benchmark` |
| `libs.plugins.shadow` | `com.gradleup.shadow` |
| `libs.plugins.asciidoctorJvm` | `org.asciidoctor.jvm.convert` |
| `libs.plugins.asciidoctorPdf` | `org.asciidoctor.jvm.pdf` |

## Adding a new catalog entry

1. Add a `versions` line if the dependency has a version not yet pinned.
2. Add a `libraries` entry referencing the version: `module = "<group>:<artifact>", version.ref = "<alias>"`.
3. For plugins: add a `plugins` entry. `build-logic` shares the same toml (its `settings.gradle.kts` loads it via `from(files("../gradle/libs.versions.toml"))`); only the plugins applied to `build-logic/convention/build.gradle.kts` itself (`kotlin("jvm")`, `kotlin("plugin.serialization")`) carry inline versions there.
4. Reference from a module's `build.gradle.kts` via `libs.foo.bar` (dashes → dots). Do not paste the coordinate.
