# Source-set rules

## Decision tree — where does this file go?

1. Does the file import any platform-specific API (`java.*`, `kotlinx.cinterop.*`, browser DOM, NodeJS modules)?
   - **No** → `commonMain` (or `commonTest` for tests).
   - **Yes** → step 2.
2. Is the import available on more than one platform?
   - **No, JVM only** → `jvmMain` (most common; covers `java.*` and the Java interop facades under `sk/ainet/java/`).
   - **No, single native target** → `<target>Main` (e.g. `iosArm64Main`).
   - **Yes, all native targets** → `nativeMain` (default-hierarchy aggregate).
   - **Yes, all Apple targets** → `appleMain`.
3. Need both a common signature and per-platform behaviour?
   - Add `public expect fun foo(...)` to `commonMain`.
   - Add `public actual fun foo(...) = ...` to each platform source set the module targets.
4. Test or production code?
   - Production → `Main` source sets (`commonMain`, `jvmMain`, …).
   - Test → matching `Test` source sets (`commonTest`, `jvmTest`, …).

## `expect` / `actual` placement

- `expect` declarations belong in `commonMain` ONLY. Anywhere else and the compiler will reject them.
- `actual` declarations belong in the narrowest source set that has the platform API. Don't put an `actual` in `commonMain`; don't broaden to `nativeMain` if only `iosArm64Main` needs it.
- `expect class` / `expect interface` may include common members defined in `commonMain` and platform-specific members supplied by the `actual`. Use this sparingly — it complicates reading.

## Test source-set rules

- `commonTest` uses `kotlin.test`. Period. Kotest is JVM-only and importing it here will not compile against native targets.
- `jvmTest` may use Kotest. Default to Kotest StringSpec for new JVM-only specs; `kotlin.test` remains acceptable for simple cases.
- `androidUnitTest` is JVM-targeted; same rules as `jvmTest`.
- The Java consumer surface (`skainet-test/skainet-test-java`) is a vanilla JVM Gradle module with `src/test/java` — JUnit 5 (`junit-jupiter`) only. Don't mix Kotlin sources in there; the whole point is to prove the API works for a Java caller.

## Dependency-direction rules per source set

- `api(project(...))` propagates the dependency's API to consumers. Use only when the public types of the consuming source set actually expose types from the dependency.
- `implementation(project(...))` does not propagate. Default choice.
- `commonMain` may depend on `commonMain` of another module. It MUST NOT depend on a platform-specific source set of another module — that breaks targets the other module supports but yours doesn't.

## KSP-generated sources

When a module consumes KSP-generated code in `commonMain`:

```kotlin
sourceSets {
    commonMain {
        kotlin.srcDir("build/generated/ksp/metadata/commonMain/kotlin")
        dependencies { api(project(":skainet-lang:skainet-lang-ksp-annotations")) }
    }
}

dependencies {
    add("kspCommonMainMetadata", project(":skainet-lang:skainet-lang-ksp-processor"))
}

tasks.configureEach {
    if (name != "kspCommonMainKotlinMetadata" &&
        (name.startsWith("compileKotlin") || name.startsWith("ksp") || name.contains("ourcesJar"))) {
        dependsOn("kspCommonMainKotlinMetadata")
    }
}
```

The trailing `tasks.configureEach { }` block is the workaround for KSP's per-target generation order — without it, the build is racy. Copy it from `skainet-lang-core/build.gradle.kts:72-83` verbatim.

## Common mistakes

| Symptom | Likely cause |
|---|---|
| Build fails on a Native target with "unresolved reference: java" | A `java.*` import leaked into `commonMain`. Move the file (or the offending import) to `jvmMain`. |
| Build passes locally but fails in CI on the WASM target | A JS-specific API (e.g. `kotlinx-browser`) was added to `commonMain` instead of `jsMain`. |
| Kotest assertions are red-underlined in `commonTest` | Kotest in `commonTest` is wrong; the import won't resolve for native compilations. |
| `expect` declared in `jvmMain` | `expect` only belongs in `commonMain`. The compiler error is misleading; check the source set. |
