# embed

Text embeddings infrastructure on Fly.io using [HuggingFace TEI](https://github.com/huggingface/text-embeddings-inference).

## Architecture

```
                    ┌─────────────────────┐
                    │   embed-proxy       │
   Internet ───────►│   (public)          │
                    │   Rust/Axum         │
                    └─────────┬───────────┘
                              │ X-Embed-Model header
                              ▼
              ┌───────────────────────────────┐
              │      Flycast (internal)       │
              └───────────────────────────────┘
                  │          │         │
                  ▼          ▼         ▼
             ┌─────────┐ ┌────────┐ ┌──────┐
             │bge-small│ │bge-base│ │bge-m3│ ...
             │  TEI    │ │  TEI   │ │  TEI │
             └─────────┘ └────────┘ └──────┘
```

## Components

- **`.deploy/fly.io/`** - TEI server deployment configs (Makefile, templates, scripts)
- **`embed-proxy/`** - Rust proxy that routes requests to backends based on model header

## Usage

```bash
curl -X POST https://embed-proxy.fly.dev/v1/embeddings \
  -H 'Content-Type: application/json' \
  -H 'X-Embed-Model: bge-small' \
  -d '{"input": "Hello world"}'
```

### Available Models

| Header Value | Model                                                                   |
| ------------ | ----------------------------------------------------------------------- |
| `bge-small`  | [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) |
| `bge-base`   | [BAAI/bge-base-en-v1.5](https://huggingface.co/BAAI/bge-base-en-v1.5)   |
| `bge-large`  | [BAAI/bge-large-en-v1.5](https://huggingface.co/BAAI/bge-large-en-v1.5) |
| `bge-m3`     | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)                       |

### Endpoints

- `POST /embed` - TEI native format
- `POST /v1/embeddings` - OpenAI-compatible format
