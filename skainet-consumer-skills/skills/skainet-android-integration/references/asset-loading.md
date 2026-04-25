# Asset loading on Android

## Where can the model file live?

| Location | Pros | Cons | Best for |
|---|---|---|---|
| `src/main/assets/<name>` | Ships with the APK; no first-run download. | Inflates APK; must be copied to a real file for random-access loaders. | Small (<50 MB) models, or APK-bundled defaults. |
| `context.cacheDir/<name>` (downloaded) | Avoids APK bloat; can be evicted by OS. | Need to handle download / first-run flow. | Models the app fetches at runtime; updateable models. |
| `context.filesDir/<name>` (downloaded, persistent) | Survives cache eviction. | Counted against app data quota. | Required-for-function models that the user shouldn't re-download. |
| External storage (`getExternalFilesDir(...)`) | User can replace the file (advanced workflows). | Permission overhead; user can corrupt it. | Power-user features only. |

## SafeTensors / GGUF need random access — copy from assets first

Loaders that need to seek (SafeTensors, GGUF) cannot work directly with `AssetManager.open(name)` — it returns a sequential `InputStream`. Copy to a real `File` once on first launch:

```kotlin
private suspend fun copyAssetIfNeeded(context: Context, assetName: String): File =
    withContext(Dispatchers.IO) {
        val target = File(context.cacheDir, assetName)
        if (!target.exists() || target.length() == 0L) {
            context.assets.open(assetName).use { input ->
                target.outputStream().use { output -> input.copyTo(output) }
            }
        }
        target
    }
```

Use `cacheDir` if the model can be re-downloaded; `filesDir` if losing it would brick the feature.

## ONNX is sequential — `assets.open(...).asSource()` works

ONNX is a single-pass parse. The `OnnxLoader.fromModelSource { ... }` lambda can return a `Source` backed directly by an asset stream:

```kotlin
import kotlinx.io.asSource

val loader = OnnxLoader.fromModelSource {
    context.assets.open("model.onnx").asSource()
}
```

No copy needed. This is the cheapest path for ONNX-only consumers.

## Verifying the asset shipped

```bash
$ ./gradlew :app:assembleDebug
$ unzip -l app/build/outputs/apk/debug/app-debug.apk | grep model
# expect to see assets/<name>
```

If the asset is missing, check that:

- The file is under `src/main/assets/`, not `src/main/res/raw/` (raw resources are different).
- `aaptOptions { noCompress("gguf", "safetensors", "onnx") }` is set in the consumer's `android { }` block — otherwise AAPT compresses the asset and the in-APK size doesn't match the file size, breaking some loaders.

## Asset noCompress setup

```kotlin
android {
    androidResources {
        noCompress += listOf("gguf", "safetensors", "onnx")
    }
}
```

This is mandatory for GGUF and SafeTensors. AAPT2 by default deflates assets to save APK space, but the loaders need the file size on disk to match the file content size.

## Streaming downloads (large models)

For multi-GB models, use a `WorkManager` job to download with retry / resume:

```kotlin
class DownloadModelWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result {
        val target = File(applicationContext.filesDir, "model.gguf")
        if (target.exists() && target.length() == expectedSize) return Result.success()
        // resumeable HTTP download → target ...
        return Result.success()
    }
}
```

Trigger from `Application.onCreate` if the model isn't present; gate the inference UI on `WorkInfo.State.SUCCEEDED`.
