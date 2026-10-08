# Lifecycle and threading on Android

## Where to host the `ExecutionContext` + `Module`

| Scope | Use when |
|---|---|
| `Application` singleton | Single-purpose ML feature, model used across the whole app. **Default choice.** |
| Hilt `@Singleton` / Koin app-scope | DI is already set up. |
| `ViewModel` (one model) | Single-screen feature with no other consumer. |
| `Service` (foreground) | Long-running background ML — transcription, monitoring. Pair with a notification. |

Do NOT host on an `Activity`. It outlives the Activity for too long (config changes, back-stack) and gets recreated on rotation.

## Coroutine scopes for `forward(...)`

| Caller | Scope |
|---|---|
| `ViewModel` | `viewModelScope.launch { withContext(Dispatchers.Default) { ... } }` |
| `Activity` / `Fragment` | `lifecycleScope.launch { withContext(Dispatchers.Default) { ... } }` |
| `Composable` (Jetpack Compose) | `LaunchedEffect(key) { ... }` ultimately delegated to a ViewModel |
| `Service` | a `CoroutineScope(SupervisorJob() + Dispatchers.Default)` owned by the Service |
| `WorkManager` | extend `CoroutineWorker`, `doWork()` is already on `Dispatchers.Default` |

The dispatcher contract:
- `Dispatchers.Main` — UI updates only.
- `Dispatchers.Default` — CPU-bound work like `forward(...)`.
- `Dispatchers.IO` — blocking IO like file copy or network.

`forward(...)` is CPU-bound; never use `Dispatchers.Main` or `Dispatchers.IO` for it.

## Intra-op threading: the `Schedule`, and the JNI kernel pool

Two separate layers (0.54.0+):

- **`ctx.schedule`** (`sk.ainet.context.schedule.Schedule`) says how an op's independent work maps onto tasks. On Android the platform default is `Schedule.Sequential` — one task, the caller's thread. (The JVM's `CoroutineSchedule` lives in `skainet-backend-cpu` *jvmMain* and is not part of the Android compilation.) A schedule never changes results.
- **The native kernels thread themselves.** With `skainet-backend-jni-cpu`, the packed-quant matmul kernels run on their own native worker pool (engaged at `outputDim >= 512`, spin-then-park — the llama.cpp trick), independent of the Kotlin dispatcher you call `forward` from. Results are bit-identical to single-threaded. So one `forward` call on `Dispatchers.Default` already uses multiple cores for the heavy matmuls.

Practical consequence: don't fan one request out over many coroutines to "parallelise" a single forward pass — run one forward per request on `Dispatchers.Default` and let the kernels thread.

## Memory pressure — `onTrimMemory(level)`

Override on `Application`:

```kotlin
override fun onTrimMemory(level: Int) {
    super.onTrimMemory(level)
    when {
        level >= ComponentCallbacks2.TRIM_MEMORY_RUNNING_CRITICAL -> dropEverything()
        level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> dropModule()
        else -> {}
    }
}
```

| Level constant | Meaning |
|---|---|
| `TRIM_MEMORY_RUNNING_MODERATE` (5) | App still in foreground; reduce caches. |
| `TRIM_MEMORY_RUNNING_LOW` (10) | App in foreground; system tight. |
| `TRIM_MEMORY_RUNNING_CRITICAL` (15) | App in foreground; system about to kill background apps. Aggressively reduce. |
| `TRIM_MEMORY_UI_HIDDEN` (20) | App's UI is no longer visible. Drop UI caches. |
| `TRIM_MEMORY_BACKGROUND` (40) | App is in the LRU. **Drop the model.** |
| `TRIM_MEMORY_MODERATE` (60) | App further in LRU. Drop more. |
| `TRIM_MEMORY_COMPLETE` (80) | App about to be killed. Drop everything. |

After dropping, set the holder reference to `null`. The next `model()` call rebuilds — make sure the rebuild path is fast (cached weight file vs. re-download).

Note on mapped GGUF weights (`AndroidGguf.loader`, default `WeightResidency.MAPPED`): tensor payloads live in file-backed page cache, which the OS evicts under pressure on its own — they never count against the ART heap cap. `onTrimMemory` still matters for everything heap-staged: the KV cache, activations, dense/repacked tensors, and your own caches.

## ABI filters

```kotlin
android.defaultConfig {
    ndk { abiFilters += "arm64-v8a" }              // primary, all modern devices
    // ndk { abiFilters += "armeabi-v7a" }          // optional, older 32-bit ARM
}
```

What to ship:

- **`arm64-v8a` only** — covers all devices from ~2017 onwards. APK is smallest.
- **`arm64-v8a` + `armeabi-v7a`** — adds ~30% to native lib size; covers older / cheaper devices.
- **`x86_64`** — emulator only (Android Studio runs x86 emulators). Don't ship in the production split.

The `skainet-backend-jni-cpu` AAR builds `.so`s for `arm64-v8a` and `x86_64`, 16 KB-page-aligned (required on Android 15+ devices with 16 KB pages). On arm64, two tiers are built from the same sources and selected at load time from `/proc/cpuinfo`: baseline `armv8-a` NEON (runs on every arm64 core) and `armv8.2-a+fp16+dotprod` (faster q4k/q6k paths, gated so Cortex-A53-class cores don't SIGILL). On 32-bit ARM devices the scalar reference kernels run; benchmark on arm64 hardware.

Use App Bundles (`AAB`) — Play Store auto-splits per-device, so you can list multiple ABIs without paying the size cost on every device.

## Locking (multi-coroutine forward)

Sharing one `DirectCpuExecutionContext` across coroutines doing inference is the normal pattern; since 0.54.0 the kernel registries are safe for concurrent reads. If two coroutines might enter `forward(...)` simultaneously, that's fine — they share the context, not the model state.

If you're updating the `Module` (loading new weights, swapping), guard with a `Mutex`:

```kotlin
private val modelMutex = Mutex()

suspend fun model(): Module<FP32, Float> = modelMutex.withLock {
    module ?: loadModel().also { module = it }
}
```

## Crashing on real device but not on emulator

The usual cause: missing ABI. Check:

- `adb shell getprop ro.product.cpu.abi` on the device — should be `arm64-v8a`.
- Your APK's `lib/` directory should contain `arm64-v8a/`.
- If shipping AAB, install with `bundletool build-apks` to verify per-device APKs.

The second-most-common cause: `noCompress` not set, AAPT compressed the asset, the loader sees a wrong size.
