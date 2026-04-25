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

The CPU backend itself doesn't multi-thread within one `forward` call (the platform's NEON / SSE intrinsics process one batch element at a time). For higher throughput, batch larger or run multiple `forward` calls concurrently.

## Concurrency safety

`DirectCpuExecutionContext` is safe to share across coroutines doing `forward` calls — the per-tensor `ops` field is stateless. The execution stats accumulator is the only shared state, and it's tolerant of concurrent updates.

A `Module` is also safe to share — its parameters are immutable in `EVAL`. In `TRAIN`, only one coroutine should run forward+backward at a time per `Module`.

## Observing intermediate layers

Don't reach for reflection; use `ForwardHooks`:

```kotlin
val ctx = DirectCpuExecutionContext(
    phase = Phase.EVAL,
    _hooks = object : ForwardHooks {
        override fun onLayerOutput(layerId: String, output: Tensor<*, *>) {
            println("$layerId: ${output.shape}")
        }
    }
)
```

Layer ids come from the optional `id = "..."` argument on each layer call (`dense(128, id = "fc1")`); auto-generated if you didn't set them.
