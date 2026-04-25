---
name: skainet-android-integration
description: Use when integrating SKaiNET into an Android app — loading model files from `assets/`, picking the CPU backend ABI (ARM, ARM64, NDK vendor-native), wiring inference to `viewModelScope` / `lifecycleScope`, handling memory pressure, and managing the JVM/Native bridge. Trigger tokens include `AssetManager`, `Context.assets.open(`, `androidNativeArm64`, `viewModelScope`, `lifecycleScope`, `OnTrimMemory`, `Application` in a SKaiNET-using app. Do NOT fire when the user is editing the SKaiNET repo's own Android source sets (the contributor `kmp` skill covers that).
version: 0.1.0
---

# skainet-android-integration

Android-specific concerns for SKaiNET consumers: how to load model files from `assets/`, which ABIs to ship, where to call `forward(...)` so the UI stays responsive, and how to react to memory pressure.

## When to use

- Building or editing an Android app that depends on SKaiNET.
- Loading a `.gguf` / `.safetensors` / `.onnx` from `src/main/assets/` (or a downloaded cache file).
- Wiring inference into a `ViewModel`, `Service`, `WorkManager`, or `Composable`.
- Configuring the Android Gradle plugin (`androidTarget`, `minSdk`, `ndk.abiFilters`).
- Diagnosing "model loads on emulator but crashes on real device" — almost always an ABI / memory issue.

## When NOT to use

- The user is editing files inside the SKaiNET repo itself (contributor `kmp` skill).
- The dependency itself is missing — `skainet-consumer-setup`.
- The user is calling SKaiNET from a non-Android JVM context — `skainet-inference` covers it without Android specifics.
- Java-only Android consumers (the ones who don't use Kotlin Coroutines) — coordinate with `skainet-java-consumer` for the Maven deps; threading still applies here.

## Hard rules

1. **`minSdk` = 24.** SKaiNET's Android target is built for `minSdk = 24`, `compileSdk = 36`. Lower is unsupported; higher is fine.
2. **Ship ARM64 at minimum; ARM32 only if you must.** The CPU backend has NEON paths for both, but ARM64 is the primary target. Do not ship x86 / x86_64 unless you specifically support emulator-only builds — production devices are ARM. Configure `ndk.abiFilters` accordingly to keep APK size down.
3. **Never call `forward(...)` on the main thread.** Use `viewModelScope.launch { withContext(Dispatchers.Default) { ... } }` from a `ViewModel`, or `lifecycleScope.launch { ... }` from an `Activity`/`Fragment`. The CPU backend can take hundreds of ms to seconds; the main thread has a 16 ms budget.
4. **Open assets with `context.assets.open(name)`. Don't decode the path as a `File` — there is no path inside the APK.** Use a `RandomAccessSource` factory that wraps the `InputStream` if the loader needs random access (some loaders do; SafeTensors and GGUF need random access — read the asset to a cache file in `context.cacheDir` and load from there if random access is required).
5. **Hold one `ExecutionContext` and one `Module` on the `Application` object** (or in a DI scope spanning the app lifetime). They're heavyweight; per-Activity construction is wasteful.
6. **React to `onTrimMemory(level)`.** When `level >= TRIM_MEMORY_BACKGROUND`, drop the `Module` (and any cached tensors); rebuild on next access. Holding multi-GB models across a backgrounded app is a sure path to LMK kills.
7. **Cache the model file once.** If the asset is a multi-GB GGUF that must be unpacked from the APK, copy it to `context.filesDir` (or `context.cacheDir`) on first launch and load from there subsequently. Loading from `assets/` repeatedly extracts on every cold start.

## Workflow

1. Add the SKaiNET BOM + `skainet-lang-core` + `skainet-backend-cpu` (see `skainet-consumer-setup`). For loaders, add `skainet-io-core` + the format-specific artifact.
2. Pick where to host the `ExecutionContext` and `Module` — usually a singleton tied to `Application` lifetime, or a Hilt/Koin app-scope binding.
3. Load the model file (asset, downloaded cache, or remote): see Canonical examples.
4. Wire the forward pass through a coroutine on `Dispatchers.Default`.
5. Handle `onTrimMemory` to release the `Module` under pressure.
6. Test on a real ARM64 device — emulators don't surface ABI / NEON issues.

## Canonical examples

**Application-scoped model holder:**

```kotlin
class SkainetApp : Application() {
    private val ctx = DirectCpuExecutionContext.create()
    private val modelMutex = Mutex()
    private var module: Module<FP32, Float>? = null

    fun executionContext(): ExecutionContext = ctx

    suspend fun model(): Module<FP32, Float> = modelMutex.withLock {
        module ?: loadModel().also { module = it }
    }

    private suspend fun loadModel(): Module<FP32, Float> = withContext(Dispatchers.IO) {
        // see "Loading from assets" below
    }

    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)
        if (level >= TRIM_MEMORY_BACKGROUND) {
            module = null  // GC reclaims; reload next forward
        }
    }
}
```

**Loading a GGUF from assets via cacheDir (random-access loaders need a real file):**

```kotlin
private suspend fun copyAssetIfNeeded(context: Context, name: String): java.io.File =
    withContext(Dispatchers.IO) {
        val target = java.io.File(context.cacheDir, name)
        if (!target.exists()) {
            context.assets.open(name).use { input ->
                target.outputStream().use { output -> input.copyTo(output) }
            }
        }
        target
    }

private suspend fun loadGGUF(context: Context): GGUFModelReader = withContext(Dispatchers.IO) {
    val file = copyAssetIfNeeded(context, "model-q4.gguf")
    GGUFModelReader(/* RandomAccessSource factory wrapping `file` */)
}
```

**Inference in a ViewModel:**

```kotlin
class ClassifyViewModel(
    private val app: SkainetApp,
    private val pre: Transform<Bitmap, Tensor<FP32, Float>>
) : AndroidViewModel(app) {

    private val _result = MutableStateFlow<List<Float>?>(null)
    val result: StateFlow<List<Float>?> = _result

    fun classify(bitmap: Bitmap) {
        viewModelScope.launch {
            val tensor = pre(bitmap)
            val module = app.model()
            val out = withContext(Dispatchers.Default) {
                module.forward(tensor, app.executionContext())
            }
            _result.value = out.toFloatList()
        }
    }
}
```

`viewModelScope` ensures the `launch` is cancelled if the `ViewModel` is destroyed mid-inference. `Dispatchers.Default` is the right pool for CPU-bound forward passes.

**Asset-resident SafeTensors via cache-first pattern (same idea as GGUF):**

```kotlin
suspend fun loadSafeTensors(context: Context, ctx: ExecutionContext, module: Module<FP32, Float>) {
    val file = copyAssetIfNeeded(context, "weights.safetensors")
    val loader = SafeTensorsParametersLoader(
        sourceProvider = { JvmFileRandomAccessSource(file) }
    )
    loader.load(ctx, FP32::class) { name, tensor ->
        module.setParameter(name, tensor)
    }
}
```

**`build.gradle.kts` (consumer Android module) — ABI filters:**

```kotlin
android {
    namespace = "com.example.skainetapp"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.skainetapp"
        minSdk = 24
        targetSdk = 36
        ndk { abiFilters += listOf("arm64-v8a") }      // primary
        // add "armeabi-v7a" only if you must support 32-bit ARM devices
    }
}

dependencies {
    implementation(platform(libs.skainet.bom))
    implementation(libs.skainet.lang.core)
    implementation(libs.skainet.backend.cpu)
    implementation(libs.skainet.io.core)
    implementation(libs.skainet.io.gguf)
}
```

## Related skills

- Adding the SKaiNET artifacts to your Android app — [`../skainet-consumer-setup/SKILL.md`](../skainet-consumer-setup/SKILL.md).
- The actual inference call (dispatcher, batch, phase) — [`../skainet-inference/SKILL.md`](../skainet-inference/SKILL.md).
- File format choice and loaders — [`../skainet-model-loading/SKILL.md`](../skainet-model-loading/SKILL.md).
- Building the input tensor from a `Bitmap` — [`../skainet-data-dsl/SKILL.md`](../skainet-data-dsl/SKILL.md) for the tensor side; preprocessing chains via `skainet-data-transform`.

## Anti-patterns

```kotlin
// WRONG — loading on every Activity onResume
override fun onResume() {
    super.onResume()
    val module = sequential<FP32, Float> { /* ... */ }   // expensive each time
    val ctx = DirectCpuExecutionContext.create()
}
```
```kotlin
// RIGHT — Application-scoped singleton
val app = applicationContext as SkainetApp
val module = app.model()
val ctx = app.executionContext()
```

```kotlin
// WRONG — assets opened as a File path (path doesn't exist inside the APK)
val reader = GGUFModelReader(JvmFileRandomAccessSource(File("file:///android_asset/model.gguf")))
```
```kotlin
// RIGHT — copy to cacheDir, load from there
val file = copyAssetIfNeeded(context, "model.gguf")
val reader = GGUFModelReader(/* source factory wrapping `file` */)
```

```kotlin
// WRONG — forward on the main thread / from a Composable directly
@Composable
fun Result(input: Tensor<FP32, Float>) {
    val out = model.forward(input, ctx)   // blocks UI for hundreds of ms
    Text(out.toString())
}
```
```kotlin
// RIGHT — collect from a StateFlow / Flow that runs forward on Default
@Composable
fun Result(viewModel: ClassifyViewModel) {
    val r by viewModel.result.collectAsState()
    Text(r?.toString() ?: "loading…")
}
```

```kotlin
// WRONG — shipping every ABI inflates APK
android.defaultConfig { /* no abiFilters → all ABIs included */ }
```
```kotlin
// RIGHT — only ARM64 (and optionally ARM32)
android.defaultConfig { ndk { abiFilters += "arm64-v8a" } }
```

```kotlin
// WRONG — ignoring memory pressure
override fun onTrimMemory(level: Int) { super.onTrimMemory(level) }
```
```kotlin
// RIGHT — drop the Module under pressure
override fun onTrimMemory(level: Int) {
    super.onTrimMemory(level)
    if (level >= TRIM_MEMORY_BACKGROUND) module = null
}
```

## References

- [`references/asset-loading.md`](references/asset-loading.md) — patterns for `assets/` vs. downloaded files vs. APK-extracted caches; loader compatibility.
- [`references/lifecycle-and-threading.md`](references/lifecycle-and-threading.md) — `viewModelScope`, `lifecycleScope`, `WorkManager`, `Service` patterns; `onTrimMemory` reference table; ABI filter recommendations.
