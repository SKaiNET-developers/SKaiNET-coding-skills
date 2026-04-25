# KMP target matrix

Authoritative source: `SKaiNET/skainet-lang/skainet-lang-core/build.gradle.kts:14-50`. New library modules should mirror this set unless there is a documented reason to drop a target.

## Targets

| Target DSL call | Source-set name | Used for |
|---|---|---|
| `jvm()` | `jvmMain` / `jvmTest` | Server-side, desktop, Java interop facades, benchmarks. |
| `android { ... }` | `androidMain` / `androidUnitTest` | Android app/library consumers. compileSdk 36, minSdk 24, JVM 11. |
| `iosArm64()` | `iosArm64Main` | Real iOS devices. |
| `iosSimulatorArm64()` | `iosSimulatorArm64Main` | iOS simulator on Apple Silicon. |
| `macosArm64()` | `macosArm64Main` | macOS desktop. |
| `linuxX64()` | `linuxX64Main` | Linux x86_64 servers / CI. |
| `linuxArm64()` | `linuxArm64Main` | Linux ARM64 (RPi, AWS Graviton). |
| `androidNativeArm32()` | `androidNativeArm32Main` | Android NDK ARM32 (vendor-native backends). |
| `androidNativeArm64()` | `androidNativeArm64Main` | Android NDK ARM64 (vendor-native backends). |
| `js { browser() }` | `jsMain` | Browser via JS. |
| `wasmJs { browser() }` | `wasmJsMain` | Browser via WASM (`@OptIn(ExperimentalWasmDsl::class)` required). |
| `wasmWasi { nodejs() }` | `wasmWasiMain` | Server-side WASM/WASI (`@OptIn(ExperimentalWasmDsl::class)` required). |

## Default hierarchy template (already enabled)

The KMP plugin's default-hierarchy creates aggregating source sets for free:

- `nativeMain` aggregates `iosArm64Main`, `iosSimulatorArm64Main`, `macosArm64Main`, `linuxX64Main`, `linuxArm64Main`, `androidNativeArm32Main`, `androidNativeArm64Main`.
- `iosMain` aggregates `iosArm64Main` and `iosSimulatorArm64Main`.
- `appleMain` aggregates `iosMain` and `macosArm64Main`.
- `linuxMain` aggregates `linuxX64Main` and `linuxArm64Main`.

Use these aggregating source sets ONLY when at least two siblings genuinely share code; otherwise place code in the narrowest source set.

## Module-target table (current state)

| Module | Targets it ships |
|---|---|
| `skainet-lang:skainet-lang-core` | full set above |
| `skainet-lang:skainet-lang-dag` | full set above |
| `skainet-data:skainet-data-api` | jvm, android, ios*, macosArm64, linux* (no js/wasm) |
| `skainet-data:skainet-data-transform` | jvm, android, ios*, macosArm64, linux* |
| `skainet-backends:skainet-backend-cpu` | jvm, android, ios*, macosArm64, linux*, androidNative* |
| `skainet-test:skainet-test-groundtruth` | matches consumers (commonMain so any target can depend) |
| `skainet-test:skainet-test-java` | jvm only (Java tests) |
| `skainet-apps/*` | jvm only (CLI) |

When in doubt, copy from the closest sibling's build script.

## Choosing targets for a new module

Default to the full canonical set. Drop a target only if:

- The module wraps a platform API that doesn't exist elsewhere (e.g. JVM-only file IO → no `wasmJs`).
- The module is an app, not a library (CLIs ship `jvm()` only).
- A native dependency isn't available on a target.

When dropping a target, leave a comment in the module's `build.gradle.kts` explaining why, so a future contributor doesn't re-add it.
