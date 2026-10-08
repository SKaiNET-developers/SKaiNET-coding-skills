# Convention plugins (`build-logic/convention`)

`build-logic` is included via `includeBuild("build-logic")` in `SKaiNET/settings.gradle.kts`. It exposes Gradle convention plugins that every module can apply by id. Convention plugins are the project's mechanism for sharing build configuration without copy-paste. Registration lives in `build-logic/convention/build.gradle.kts` (`gradlePlugin { plugins { register(...) } }`); `sk.ainet.dokka` is the exception — it is a precompiled script plugin (`build-logic/convention/src/main/kotlin/sk.ainet.dokka.gradle.kts`).

## Currently published

### `sk.ainet.multiplatform` (`SkainetMultiplatformPlugin`)

SKaiNET's standard KMP module setup — replaces the hand-copied target list, `android { }` block, `explicitApi()`, `kotlin-test` wiring and Karma hardening:

- Creates the default target set (`jvm`, `js`, `wasmJs`, `wasmWasi`, `apple`, `linux`); a module diverges via the `skainet.targets` property in its own `gradle.properties` (`androidNative` opt-in, `none` = declare targets yourself).
- Contributes the `skainet { }` extension: `namespace` (required with the AGP KMP plugin), `androidJvmTarget` (default `JVM_11`; `skainet-io` family uses `JVM_1_8`), `explicitApi` (default true), `expectActualClasses`, `kotlinTestInCommonTest` (default true).
- Fills in `compileSdk`/`minSdk` from the catalog for the Android target.
- Fails js/wasmJs modules loudly when the root project doesn't apply `sk.ainet.npm-pins`.

```kotlin
plugins {
    id("sk.ainet.multiplatform")
    alias(libs.plugins.androidMultiplatformLibrary)   // opt into Android
}
skainet { namespace = "sk.ainet.pipeline" }
```

### `sk.ainet.dokka` (precompiled script plugin)

Configures Dokka 2.x consistently across modules:

- Restricts visibility to `public` declarations, suppresses inherited members and generated files.
- Suppresses native source sets that use cinterop, and the `androidMain` source set of modules with a shared `src/jvmAndroidMain` directory (the shared API is documented once, via jvm).
- Wires source links to GitHub.

A module SHOULD apply `id("sk.ainet.dokka")` if it has a public API. Apps under `skainet-apps/` and the test infrastructure (`skainet-test-*`) typically don't. Remember to also add the module to the root `dokka(project(...))` aggregation block.

### `sk.ainet.documentation` (`DocumentationPlugin`)

Applied on the root project (`alias(libs.plugins.skainet.docs)`). Registers the docs pipeline tasks: `generateDocs` (operator docs from KSP-emitted `operators.json` into Antora), `generateKernelMatrix` (kernel × platform support matrix from `kernel-support.json`), and `validateOperatorSchema`. Configured through the root `documentation { }` extension.

### `sk.ainet.transformers.bom-coverage` (`BomCoveragePlugin`)

Applied by `skainet-bom`. Populates the BOM's constraints automatically: every sibling subproject that applies `com.vanniktech.maven.publish` becomes an `api` constraint, sorted by Gradle path. Opt a published module out via `bomCoverage.excludePublished`.

### `sk.ainet.npm-pins` (`NpmPinsPlugin`) and `sk.ainet.maven-pins` (`MavenPinsPlugin`)

Root-project-only security plugins. `npm-pins` forces catalog-declared npm versions into both `kotlin-js-store` yarn lockfiles via Yarn resolutions (`skainet { npmPins { pin("ws", libs.versions.npm.ws) } }`, optionally scoped with `NpmPinTarget.JS`) and adds `verifyNpmPins`; regenerate lockfiles with `./gradlew kotlinUpgradeYarnLock kotlinWasmUpgradeYarnLock`, never by hand. `maven-pins` does the same for transitive Maven coordinates through `resolutionStrategy`, verified by `verifyMavenPins` on `check`.

## Adding a new convention plugin

When the same Gradle configuration block is being copied into 3+ modules, lift it into a convention plugin.

1. Create `build-logic/convention/src/main/kotlin/sk/ainet/buildlogic/<area>/<Name>Plugin.kt` with a class implementing `org.gradle.api.Plugin<Project>` (or a `sk.ainet.<name>.gradle.kts` precompiled script for simple cases).
2. Register it in `build-logic/convention/build.gradle.kts`:
   ```kotlin
   gradlePlugin {
       plugins {
           register("SKaiNet<Name>") {
               id = "sk.ainet.<name>"
               implementationClass = "sk.ainet.buildlogic.<area>.<Name>Plugin"
           }
       }
   }
   ```
3. Add a catalog entry in `gradle/libs.versions.toml`:
   ```toml
   [plugins]
   skainet-<name> = { id = "sk.ainet.<name>" }
   ```
4. Apply from a module:
   ```kotlin
   plugins { alias(libs.plugins.skainet.<name>) }
   ```
   or `id("sk.ainet.<name>")` if you don't want to go through the catalog (acceptable for in-tree convention plugins because there's no version to track).

Note: build-logic needs KGP/AGP types? Add them as `compileOnly` (`libs.kotlin.gradlePlugin` / `libs.android.gradlePlugin`), never `implementation` — a runtime copy would load a second KGP/AGP in a different classloader and break `getByType(...)` with ClassCastExceptions.

## Convention plugins vs root `subprojects { }`

Cross-cutting *opt-in* concerns go through convention plugins: modules choose what they need, the configuration is versioned Kotlin code, and it surfaces in IDE/Gradle introspection as real plugins. The root `build.gradle.kts` keeps a small `subprojects { }` block for the truly unconditional project-wide settings (JDK 21 floor, `JvmTarget.JVM_21` on JVM targets, Java `--release 21`, test heap, kover) — don't grow it; anything a module could reasonably opt out of belongs in a convention plugin or a catalog alias.
