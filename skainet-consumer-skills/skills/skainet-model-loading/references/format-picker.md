# Format picker

## "What format is this file?"

| File extension | Format | Magic bytes |
|---|---|---|
| `.gguf` | GGUF (llama.cpp / ollama) | `GGUF` |
| `.safetensors` | SafeTensors (HuggingFace) | first 8 bytes are header length (LE u64) |
| `.onnx` | ONNX (protobuf) | protobuf framing — `ir_version` field |
| `.json` (SKaiNET-emitted) | SKaiNET JSON serialisation | top-level `"version"` + `"graph"` keys |
| `.bin` | Ambiguous — could be raw weights, PyTorch pickle, or proprietary | inspect with `file(1)` |
| `.pt` / `.pth` | PyTorch pickle — NOT directly supported | convert to SafeTensors or ONNX first |

## "Which loader for which format?"

| Format | Loader | Artifact |
|---|---|---|
| GGUF | `GGUFModelReader` | `sk.ainet.core:skainet-io-gguf` |
| SafeTensors | `SafeTensorsParametersLoader` | `sk.ainet.core:skainet-io-safetensors` |
| ONNX | `OnnxLoader.fromModelSource` | `sk.ainet.core:skainet-io-onnx` |
| SKaiNET JSON | (tooling in `skainet-compile-json`) | `sk.ainet.core:skainet-compile-json` |

## "I have a model in format X, which should I convert to?"

| Source | Converter | Target |
|---|---|---|
| PyTorch state_dict | `model.save_pretrained(...)` (Python) | SafeTensors |
| PyTorch model | `torch.onnx.export(...)` (Python) | ONNX |
| TensorFlow SavedModel | `tf2onnx` | ONNX |
| HuggingFace transformers | already ships SafeTensors + GGUF for many models | SafeTensors / GGUF |

SKaiNET itself does not ship Python conversion tooling; conversion lives in the source ecosystem. SKaiNET consumes the canonical formats directly.

## When format choice matters at runtime

- **GGUF**: best for LLMs because weights can be quantised in-format (Q4_0, Q8_0) and the loader streams. Use when memory is tight.
- **SafeTensors**: best for general transformer weights — fast load, safe (no pickle), good HuggingFace ecosystem support. Pair with a SKaiNET-DSL model definition.
- **ONNX**: best when you have a trained graph from another framework and want SKaiNET to consume it whole. Higher coupling to `skainet-compile-*` because the graph needs to lower into a runnable `Module`.
- **JSON**: best for round-tripping models you built with the SKaiNET DSL — diff-friendly, version-controllable.

## Common mistakes

- Treating SafeTensors as a "model" — it's weights only. You still need a SKaiNET `Module` (built with `sequential` or `dag`) to bind the weights into.
- Using `OnnxLoader` to extract weights from an ONNX file when SafeTensors would be cleaner — ONNX loading parses the whole graph; if you only need weights, ask whether SafeTensors is available.
- Loading GGUF in-memory all at once via a `ByteArray` source — defeats GGUF's streaming model. Use a `RandomAccessSource` factory that mmaps the file.
