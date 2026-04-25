# Convention plugins (`build-logic/convention`)

`build-logic` is included via `includeBuild("build-logic")` in `SKaiNET/settings.gradle.kts`. It exposes Gradle convention plugins that every module can apply by id. Convention plugins are the project's mechanism for sharing build configuration without copy-paste.

## Currently published

### `sk.ainet.documentation` (a.k.a. `sk.ainet.dokka`)

Configures Dokka 2.x consistently across modules:

- Hides native and cinterop source sets from generated documentation.
- Restricts visibility to `public` declarations only.
- Suppresses inherited members (otherwise every `public class` would document every method on `Any`).

Module application:
```kotlin
plugins {
    id("sk.ainet.dokka")
}
```

A module SHOULD apply this plugin if it has a public API. Apps under `skainet-apps/` and the test infrastructure (`skainet-test-*`) typically don't.

The plugin is registered in `build-logic/convention/build.gradle.kts` with `implementationClass = "DocumentationPlugin"`.

## Adding a new convention plugin

When the same Gradle configuration block is being copied into 3+ modules, lift it into a convention plugin.

1. Create `build-logic/convention/src/main/kotlin/sk/ainet/buildlogic/<Name>Plugin.kt` with a class implementing `org.gradle.api.Plugin<Project>`.
2. Register it in `build-logic/convention/build.gradle.kts`:
   ```kotlin
   gradlePlugin {
       plugins {
           register("skainet<Name>") {
               id = "sk.ainet.<name>"
               implementationClass = "sk.ainet.buildlogic.<Name>Plugin"
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
   plugins { alias(libs.plugins.skainet-<name>) }
   ```
   or `id("sk.ainet.<name>")` if you don't want to go through the catalog (acceptable for in-tree convention plugins because there's no version to track).

## Why convention plugins, not subproject `subprojects { }` blocks

- Convention plugins are opt-in per module. Modules choose what they need.
- They surface in IDE/Gradle introspection as actual plugins, with their own KDoc and lifecycle.
- They version-control as Kotlin code, not Groovy DSL strings.
- They can be unit-tested with `kotlin-compile-testing` if needed.

`subprojects { }` in the root `build.gradle.kts` is forbidden in this project — every cross-cutting concern goes through a convention plugin or a catalog alias.
