# Forward pass

## Calling forward

`Module<T, V>` (the value `sequential<T, V> { }` returns) exposes:

```kotlin
public fun forward(input: Tensor<T, V>, ctx: ExecutionContext): Tensor<T, V>
```

`input.shape` MUST match what the model declared via `input(...)`:

| `input(...)` declaration | Expected `input.shape` |
|---|---|
| `input(784)` | `[batch, 784]` |
| `input(intArrayOf(1, 28, 28))` | `[batch, 1, 28, 28]` |
| `input(intArrayOf(3, 224, 224))` | `[batch, 3, 224, 224]` |

The leading `batch` dimension is implicit. For a single sample, `batch = 1`.

## Output shape

The output shape comes from the last layer:

| Last layer | Output shape (with batch dim) |
|---|---|
| `dense(N)` | `[batch, N]` |
| `softmax(dim = -1)` after `dense(N)` | `[batch, N]` |
| `conv2d(C_out, ...)` followed by no `flatten` | `[batch, C_out, H, W]` |
| `flatten()` after `conv2d` | `[batch, C_out * H * W]` |

If the output shape isn't what you expect, the model is wrong — check the layer chain before suspecting `forward`.

## Batching

There is no separate batched-forward API. Batching is a leading shape dimension:

```kotlin
val singleSample = tensor(...) { tensor { shape(1, 784) { ... } } }
val batchOf32   = tensor(...) { tensor { shape(32, 784) { ... } } }

val outSingle = model.forward(singleSample, ctx)   // [1, 10]
val outBatch  = model.forward(batchOf32,   ctx)    // [32, 10]
```

CPU backend processes the batch in one pass — generally faster than 32 single-sample forwards because of better cache reuse.

## Reading the output

Three ways to consume the output `Tensor<T, V>`:

1. **As another tensor input** (chained inference, ensemble) — pass straight back into another `forward` call.
2. **As a primitive array** for application code:
   ```kotlin
   val data = TensorAssertions.extractFloatData(out)   // FloatArray
   ```
   (Note: `TensorAssertions` lives in `skainet-test-groundtruth`, available to consumers if added.)
3. **Element by element** via `out.data[indices...]` — fine for a single argmax / single read; expensive for bulk extraction.

## Threading

Forward is synchronous and CPU-bound:

| Caller | Right dispatcher |
|---|---|
| JVM CLI | direct call — process is the dispatcher. |
| Server (Spring Boot, Ktor) | dedicated `ExecutorService` for ML, OR `Dispatchers.Default` from a coroutine. |
| Android — UI handler | `withContext(Dispatchers.Default) { ... }` from a `lifecycleScope.launch { }`. |
| KMP Native (iOS) | a worker thread / dispatcher; never the main runloop. |

Whether one `forward` call multi-threads internally is the context's `Schedule` (0.54.0+): on the JVM the default is `CoroutineSchedule.hardware()`, so scheduled ops (scaled-dot-product attention first) spread their independent `(batch, head)` units across cores; on Android, Kotlin/Native and JS/Wasm the default is `Schedule.Sequential`. Results are bit-identical either way. For many concurrent `forward` calls on a server, consider `ctx.withSchedule(Schedule.Sequential) { ... }` to avoid oversubscribing the pool — see `execution-context.md`.

## Concurrency safety

Sharing one `DirectCpuExecutionContext` across coroutines doing `forward` calls is the normal pattern; since 0.54.0 the kernel registries (`KernelDispatch`, `KernelRegistry`) are safe for concurrent reads.

A `Module` is also safe to share for inference — its parameters are not mutated in `EVAL`. In `TRAIN`, only one coroutine should run forward+backward at a time per `Module`.

## Observing intermediate layers

Don't reach for reflection; use `ForwardHooks` (`sk.ainet.lang.nn.hooks`):

```kotlin
val ctx = DirectCpuExecutionContext(
    phase = Phase.EVAL,
    _hooks = object : ForwardHooks {
        override fun onForwardBegin(module: ModuleNode, input: Any) {}
        override fun onForwardEnd(module: ModuleNode, input: Any, output: Any) {
            println("${module.name}: ${(output as? Tensor<*, *>)?.shape}")
        }
    }
)
```

`Module.forward` invokes the hooks around every module in the tree; `module.name` / `module.path` identify the layer. Ids come from the optional `id = "..."` argument on each layer call (`dense(128, id = "fc1")`); auto-generated if you didn't set them.
