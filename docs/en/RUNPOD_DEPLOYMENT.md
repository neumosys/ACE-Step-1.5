# ACE-Step 1.5 RunPod Serverless Deployment

This guide covers deploying ACE-Step 1.5 as a RunPod serverless worker.

## Features

- **Text-to-Music Generation**: Generate music from text prompts and lyrics
- **LLM Chain-of-Thought**: Optional 5Hz Language Model for intelligent metadata and audio code generation
- **Multiple Task Types**: text2music, cover, repaint, lego, extract, complete
- **Batch Generation**: Generate multiple samples in one request
- **S3 Integration**: Automatic upload of generated audio to S3-compatible storage

## Quick Start

### 1. Build the Docker Image

```bash
cd ACE-Step-1.5
docker build -f Dockerfile.runpod -t your-username/ace-step-1.5:latest .
```

### 2. Push to Docker Hub

```bash
docker push your-username/ace-step-1.5:latest
```

### 3. Create RunPod Serverless Endpoint

1. Go to [RunPod Console](https://www.runpod.io/console/serverless)
2. Create a new Serverless Endpoint
3. Use your Docker image: `your-username/ace-step-1.5:latest`
4. Configure environment variables (see below)
5. Set GPU type (recommended: RTX 4090, A100, or H100)

## Environment Variables

### Required

| Variable                | Description                 |
| ----------------------- | --------------------------- |
| `S3_BUCKET_NAME`        | S3 bucket for audio uploads |
| `AWS_ACCESS_KEY_ID`     | AWS access key              |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key              |

### Optional

| Variable              | Default               | Description                                 |
| --------------------- | --------------------- | ------------------------------------------- |
| `AWS_REGION`          | `us-east-1`           | AWS region                                  |
| `S3_ENDPOINT_URL`     | (none)                | Custom S3 endpoint (for R2, MinIO, etc.)    |
| `CHECKPOINT_DIR`      | `/app/checkpoints`    | Model checkpoints directory                 |
| `DIT_MODEL`           | `acestep-v15-turbo`   | DiT model to use                            |
| `LM_MODEL`            | `acestep-5Hz-lm-1.7B` | LLM model to use                            |
| `LM_BACKEND`          | `vllm`                | LLM backend (`vllm` or `pt`)                |
| `DEVICE`              | `cuda`                | Device (`cuda`, `cpu`, or `auto`)           |
| `USE_FLASH_ATTENTION` | `true`                | Enable flash attention                      |
| `OFFLOAD_TO_CPU`      | `false`               | Offload models to CPU when not in use       |
| `ENABLE_LLM`          | `true`                | Enable LLM (set `false` for faster startup) |

## API Reference

### Input Parameters

#### Core Parameters

| Parameter      | Type   | Default        | Description                                                                  |
| -------------- | ------ | -------------- | ---------------------------------------------------------------------------- |
| `task_type`    | string | `"text2music"` | Task type: `text2music`, `cover`, `repaint`, `lego`, `extract`, `complete`   |
| `caption`      | string | `""`           | Main prompt describing the music (< 512 chars)                               |
| `lyrics`       | string | `""`           | Lyrics for the music, use `"[Instrumental]"` for instrumental (< 4096 chars) |
| `instrumental` | bool   | `false`        | Force instrumental generation                                                |

#### Music Metadata

| Parameter        | Type   | Default     | Description                                      |
| ---------------- | ------ | ----------- | ------------------------------------------------ |
| `duration`       | float  | `-1`        | Target duration in seconds (10-600, -1 for auto) |
| `bpm`            | int    | `null`      | BPM (30-300, null for auto)                      |
| `keyscale`       | string | `""`        | Musical key (e.g., `"C Major"`, `"Am"`)          |
| `timesignature`  | string | `""`        | Time signature: `"2"`, `"3"`, `"4"`, or `"6"`    |
| `vocal_language` | string | `"unknown"` | Language code: `en`, `zh`, `ja`, etc.            |

#### Generation Parameters

| Parameter         | Type   | Default  | Description                                    |
| ----------------- | ------ | -------- | ---------------------------------------------- |
| `inference_steps` | int    | `8`      | Diffusion steps (8 for turbo, 32-100 for base) |
| `guidance_scale`  | float  | `7.0`    | CFG strength                                   |
| `seed`            | int    | `-1`     | Seed for reproducibility (-1 for random)       |
| `batch_size`      | int    | `1`      | Number of samples to generate (1-8)            |
| `audio_format`    | string | `"flac"` | Output format: `mp3`, `wav`, `flac`            |

#### LLM Parameters

| Parameter          | Type  | Default | Description                           |
| ------------------ | ----- | ------- | ------------------------------------- |
| `thinking`         | bool  | `true`  | Enable LLM chain-of-thought reasoning |
| `lm_temperature`   | float | `0.85`  | LLM sampling temperature (0.0-2.0)    |
| `lm_cfg_scale`     | float | `2.0`   | LLM CFG scale                         |
| `use_cot_metas`    | bool  | `true`  | Let LLM generate music metadata       |
| `use_cot_caption`  | bool  | `true`  | Let LLM enhance caption               |
| `use_cot_language` | bool  | `true`  | Let LLM detect language               |

#### Advanced DiT Parameters

| Parameter            | Type  | Default | Description                                  |
| -------------------- | ----- | ------- | -------------------------------------------- |
| `use_adg`            | bool  | `false` | Use Adaptive Dual Guidance (base model only) |
| `cfg_interval_start` | float | `0.0`   | CFG start ratio (0.0-1.0)                    |
| `cfg_interval_end`   | float | `1.0`   | CFG end ratio (0.0-1.0)                      |
| `shift`              | float | `1.0`   | Timestep shift factor                        |

#### Audio-to-Audio Parameters

| Parameter              | Type   | Default | Description                                              |
| ---------------------- | ------ | ------- | -------------------------------------------------------- |
| `reference_audio`      | string | `null`  | Reference audio (URL or base64) for cover/style transfer |
| `src_audio`            | string | `null`  | Source audio (URL or base64) for repaint/lego tasks      |
| `audio_codes`          | string | `""`    | Pre-computed audio codes (advanced)                      |
| `repainting_start`     | float  | `0.0`   | Start time for repaint region (seconds)                  |
| `repainting_end`       | float  | `-1`    | End time for repaint region (-1 for end)                 |
| `audio_cover_strength` | float  | `1.0`   | Reference audio influence (0.0-1.0)                      |

### Output Format

```json
{
  "audios": [
    {
      "url": "https://s3.amazonaws.com/bucket/uuid.flac?...",
      "key": "unique-audio-key",
      "seed": 12345,
      "sample_rate": 48000
    }
  ],
  "audio_url": "https://s3.amazonaws.com/bucket/uuid.flac?...",
  "format": "flac",
  "task_type": "text2music",
  "generation_time": 15.5,
  "status_message": "...",
  "lm_metadata": {
    "bpm": 120,
    "keyscale": "C Major",
    "duration": 30,
    "vocal_language": "en"
  },
  "time_costs": {
    "lm_phase1_time": 2.5,
    "lm_phase2_time": 3.0,
    "dit_total_time_cost": 10.0,
    "pipeline_total_time": 15.5
  }
}
```

## Examples

### Basic Text-to-Music

```json
{
  "input": {
    "task_type": "text2music",
    "caption": "A cinematic orchestral piece with dramatic strings and percussion",
    "duration": 30,
    "inference_steps": 8
  }
}
```

### With Lyrics

```json
{
  "input": {
    "task_type": "text2music",
    "caption": "Pop song, upbeat, electronic",
    "lyrics": "[Verse 1]\nHello world, this is my song\nSinging along, nothing is wrong\n\n[Chorus]\nLa la la, we're having fun\nUnder the bright morning sun",
    "duration": 60,
    "vocal_language": "en"
  }
}
```

### Cover/Style Transfer

```json
{
  "input": {
    "task_type": "cover",
    "caption": "Jazz version with smooth saxophone",
    "src_audio": "https://example.com/original.wav",
    "audio_cover_strength": 0.7,
    "duration": 30
  }
}
```

### Repaint (Selective Editing)

```json
{
  "input": {
    "task_type": "repaint",
    "caption": "Add an energetic drum solo",
    "src_audio": "https://example.com/original.wav",
    "repainting_start": 10.0,
    "repainting_end": 20.0
  }
}
```

### Batch Generation

```json
{
  "input": {
    "task_type": "text2music",
    "caption": "Lo-fi hip hop beats to study to",
    "duration": 30,
    "batch_size": 4,
    "seed": -1
  }
}
```

### DiT-Only Mode (No LLM)

```json
{
  "input": {
    "task_type": "text2music",
    "caption": "Ambient electronic music",
    "thinking": false,
    "duration": 30,
    "bpm": 90,
    "keyscale": "A Minor"
  }
}
```

## Model Variants

### DiT Models

| Model                      | Description               | Steps  |
| -------------------------- | ------------------------- | ------ |
| `acestep-v15-turbo`        | Fast generation (default) | 8      |
| `acestep-v15-turbo-shift1` | Turbo with shift=1        | 8      |
| `acestep-v15-turbo-shift3` | Turbo with shift=3        | 8      |
| `acestep-v15-base`         | High quality, slower      | 32-100 |
| `acestep-v15-sft`          | Supervised fine-tuned     | 32-100 |

### LLM Models

| Model                 | Description        | VRAM  |
| --------------------- | ------------------ | ----- |
| `acestep-5Hz-lm-0.6B` | Lightweight        | ~2GB  |
| `acestep-5Hz-lm-1.7B` | Balanced (default) | ~4GB  |
| `acestep-5Hz-lm-4B`   | Premium quality    | ~10GB |

## Local Testing

Test the handler locally before deployment:

```bash
# Set environment variables
export S3_BUCKET_NAME=your-bucket
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export CHECKPOINT_DIR=/path/to/checkpoints

# Run test
python test_handler_runpod.py --caption "A relaxing ambient piece"

# With more options
python test_handler_runpod.py \
  --caption "Electronic dance music" \
  --duration 30 \
  --inference_steps 8 \
  --batch_size 2
```

## GPU Requirements

| Configuration    | Minimum VRAM | Recommended |
| ---------------- | ------------ | ----------- |
| DiT-only (turbo) | 8GB          | RTX 3090+   |
| DiT + LLM 0.6B   | 12GB         | RTX 4080+   |
| DiT + LLM 1.7B   | 16GB         | RTX 4090    |
| DiT + LLM 4B     | 24GB+        | A100/H100   |

## Troubleshooting

### Out of Memory

- Set `ENABLE_LLM=false` to disable LLM
- Use smaller LLM: `LM_MODEL=acestep-5Hz-lm-0.6B`
- Set `OFFLOAD_TO_CPU=true` for low VRAM GPUs
- Reduce `batch_size` to 1

### Slow Startup

- LLM tokenizer loading takes ~90 seconds on first run
- Set `ENABLE_LLM=false` for faster startup (no chain-of-thought)
- Use `LM_BACKEND=pt` instead of `vllm` for simpler setup

### Flash Attention Errors

- Set `USE_FLASH_ATTENTION=false` to use SDPA instead
- Ensure CUDA version matches (12.8 recommended)
