# ACE-Step 1.5 RunPod API Documentation

Complete API reference for the ACE-Step 1.5 RunPod serverless endpoint.

## Table of Contents

- [Overview](#overview)
- [Task Types](#task-types)
  - [text2music](#text2music) - Generate music from text
  - [cover](#cover) - Create a cover version
  - [repaint](#repaint) - Replace a time region
  - [lego](#lego) - Add a single instrument track
  - [extract](#extract) - Extract/isolate a track (stem separation)
  - [complete](#complete) - Add multiple instrument tracks
  - [understand](#understand) - Analyze audio and extract metadata
- [Common Parameters](#common-parameters)
- [Response Format](#response-format)
- [Track Names](#track-names)

---

## Overview

The ACE-Step 1.5 API provides AI-powered music generation through RunPod serverless endpoints. All requests are sent as JSON with an `input` object containing parameters.

**Base Request Format:**

```json
{
  "input": {
    "task_type": "text2music"
    // ... other parameters
  }
}
```

**Audio Input Formats:**

- `src_audio` and `reference_audio` accept:
  - HTTP/HTTPS URLs to audio files
  - Base64-encoded audio data
  - Data URI format (`data:audio/mp3;base64,...`)

---

## Task Types

### text2music

Generate music from scratch using text prompts.

**Use Case:** Creating original songs from descriptions and lyrics.

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `caption` | string | Description of the music style, mood, instruments |

**Optional Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lyrics` | string | "" | Song lyrics (use `[Instrumental]` for no vocals) |
| `instrumental` | bool | false | Force instrumental generation |
| `duration` | float | -1 | Target duration in seconds (-1 for auto) |
| `bpm` | int | null | Beats per minute (null for auto) |
| `keyscale` | string | "" | Musical key (e.g., "C Major", "Am") |
| `auto_lrc` | bool | false | Generate LRC lyrics timestamps |

**Example Request:**

```json
{
  "input": {
    "task_type": "text2music",
    "caption": "Upbeat indie rock song with jangly guitars and energetic drums",
    "lyrics": "[Verse 1]\nWalking down the street today\nEverything seems bright and okay\n\n[Chorus]\nThis is the moment we've been waiting for",
    "duration": 120,
    "bpm": 128,
    "keyscale": "G Major",
    "vocal_language": "en",
    "batch_size": 2,
    "auto_lrc": true
  }
}
```

**Example Response:**

```json
{
  "audios": [
    {
      "url": "https://s3.../uuid1.flac",
      "seed": 12345,
      "sample_rate": 48000
    },
    {
      "url": "https://s3.../uuid2.flac",
      "seed": 67890,
      "sample_rate": 48000
    }
  ],
  "audio_url": "https://s3.../uuid1.flac",
  "format": "flac",
  "task_type": "text2music",
  "generation_time": 45.2,
  "lrc": [
    {
      "lrc_text": "[00:05.23]Walking down the street today\n[00:10.45]Everything seems bright and okay",
      "sample_index": 0
    }
  ],
  "lm_metadata": {
    "bpm": 128,
    "keyscale": "G Major",
    "duration": 120
  }
}
```

---

### cover

Create a cover version of an existing song, preserving structure but changing style.

**Use Case:** Style transfer, creating alternate versions of songs.

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `src_audio` | string | URL or base64 of the source audio |
| `caption` | string | Description of the new style |

**Optional Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `audio_cover_strength` | float | 1.0 | How closely to follow source (0.0-1.0, lower = more style transfer) |
| `reference_audio` | string | null | Additional style reference audio |

**Example Request:**

```json
{
  "input": {
    "task_type": "cover",
    "src_audio": "https://your-bucket.s3.amazonaws.com/original-song.mp3",
    "caption": "Jazz lounge version with smooth piano and soft drums",
    "audio_cover_strength": 0.7
  }
}
```

---

### repaint

Replace a specific time region of audio with new generated content.

**Use Case:** Fixing sections, extending songs, replacing parts.

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `src_audio` | string | URL or base64 of the source audio |
| `caption` | string | Description of the replacement content |

**Optional Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repainting_start` | float | 0.0 | Start time in seconds |
| `repainting_end` | float | -1 | End time in seconds (-1 for end of file) |

**Example Request:**

```json
{
  "input": {
    "task_type": "repaint",
    "src_audio": "https://your-bucket.s3.amazonaws.com/song.mp3",
    "caption": "Energetic guitar solo with distortion",
    "repainting_start": 60.0,
    "repainting_end": 90.0
  }
}
```

---

### lego

Add a single instrument track to existing audio. Like stacking Lego blocks.

**Use Case:** Adding drums to a guitar track, adding bass to a melody.

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `src_audio` | string | URL or base64 of the source audio |
| `track_name` | string | Which instrument to generate (see [Track Names](#track-names)) |

**Optional Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `caption` | string | "" | Description of the track style |
| `repainting_start` | float | 0.0 | Start time for the new track |
| `repainting_end` | float | -1 | End time for the new track |
| `output_mode` | string | "stems" | `"stems"` = new track only, `"mixed"` = mixed with source |
| `mix_volume_source` | float | 1.0 | Source audio volume when mixing (0.0-2.0) |
| `mix_volume_generated` | float | 1.0 | Generated track volume when mixing (0.0-2.0) |

**Example Request (stems only):**

```json
{
  "input": {
    "task_type": "lego",
    "src_audio": "https://your-bucket.s3.amazonaws.com/guitar-track.mp3",
    "track_name": "drums",
    "caption": "Tight rock drums with punchy kick and crisp snare"
  }
}
```

**Example Request (pre-mixed output):**

```json
{
  "input": {
    "task_type": "lego",
    "src_audio": "https://your-bucket.s3.amazonaws.com/guitar-track.mp3",
    "track_name": "drums",
    "caption": "Tight rock drums with punchy kick and crisp snare",
    "output_mode": "mixed",
    "mix_volume_source": 1.0,
    "mix_volume_generated": 0.8
  }
}
```

---

### extract

Extract/isolate a specific instrument track from mixed audio (stem separation).

**Use Case:** Isolating vocals, extracting drums, creating stems.

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `src_audio` | string | URL or base64 of the mixed audio |
| `track_name` | string | Which instrument to extract (see [Track Names](#track-names)) |

**Example Request:**

```json
{
  "input": {
    "task_type": "extract",
    "src_audio": "https://your-bucket.s3.amazonaws.com/full-mix.mp3",
    "track_name": "vocals"
  }
}
```

---

### complete

Add multiple instrument tracks to existing audio at once.

**Use Case:** Creating full backing tracks from vocals, auto-arranging.

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `src_audio` | string | URL or base64 of the source audio |
| `complete_track_classes` | array | List of tracks to add (see [Track Names](#track-names)) |

**Optional Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `caption` | string | "" | Description of the arrangement style |
| `output_mode` | string | "stems" | `"stems"` = new tracks only, `"mixed"` = mixed with source |
| `mix_volume_source` | float | 1.0 | Source audio volume when mixing (0.0-2.0) |
| `mix_volume_generated` | float | 1.0 | Generated tracks volume when mixing (0.0-2.0) |

**Example Request (stems only):**

```json
{
  "input": {
    "task_type": "complete",
    "src_audio": "https://your-bucket.s3.amazonaws.com/vocals-only.mp3",
    "complete_track_classes": ["drums", "bass", "guitar", "keyboard"],
    "caption": "Pop rock backing with driving rhythm and melodic keys"
  }
}
```

**Example Request (pre-mixed full song):**

```json
{
  "input": {
    "task_type": "complete",
    "src_audio": "https://your-bucket.s3.amazonaws.com/vocals-only.mp3",
    "complete_track_classes": ["drums", "bass", "guitar", "keyboard"],
    "caption": "Pop rock backing with driving rhythm and melodic keys",
    "output_mode": "mixed"
  }
}
```

---

### understand

Analyze audio and extract metadata including caption, lyrics, BPM, key, etc.

**Use Case:** Music analysis, lyrics extraction, BPM detection, generating descriptions.

**Required Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `src_audio` | string | URL or base64 of the audio to analyze |

**Optional Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lm_temperature` | float | 0.85 | Creativity of analysis (lower = more deterministic) |

**Example Request:**

```json
{
  "input": {
    "task_type": "understand",
    "src_audio": "https://your-bucket.s3.amazonaws.com/song.mp3"
  }
}
```

**Example Response:**

```json
{
  "task_type": "understand",
  "caption": "An upbeat pop rock song with energetic electric guitars, driving drums, and catchy vocal melodies. The production features bright synths and a powerful chorus.",
  "lyrics": "[Verse 1]\nWalking through the city lights\nEverything feels so alive tonight\n\n[Chorus]\nWe're gonna dance until the morning comes",
  "bpm": 128,
  "duration": 195.5,
  "keyscale": "G Major",
  "language": "en",
  "timesignature": "4/4",
  "processing_time": 3.45
}
```

---

## Common Parameters

These parameters work with all generation tasks (not `understand`):

### Text & Content

| Parameter        | Type   | Default   | Description                                    |
| ---------------- | ------ | --------- | ---------------------------------------------- |
| `caption`        | string | ""        | Main prompt describing the music               |
| `lyrics`         | string | ""        | Lyrics (use `[Instrumental]` for instrumental) |
| `instrumental`   | bool   | false     | Force instrumental generation                  |
| `vocal_language` | string | "unknown" | Language code: en, zh, ja, ko, etc.            |

### Music Metadata

| Parameter       | Type   | Default | Description                                        |
| --------------- | ------ | ------- | -------------------------------------------------- |
| `duration`      | float  | -1      | Target duration in seconds (-1 for auto, max ~600) |
| `bpm`           | int    | null    | Beats per minute (null for auto, range 30-300)     |
| `keyscale`      | string | ""      | Musical key (e.g., "C Major", "F# minor")          |
| `timesignature` | string | ""      | Time signature: "2", "3", "4", or "6"              |

### Generation Settings

| Parameter         | Type   | Default | Description                                    |
| ----------------- | ------ | ------- | ---------------------------------------------- |
| `inference_steps` | int    | 8       | Diffusion steps (8 for turbo, 32-100 for base) |
| `guidance_scale`  | float  | 7.0     | CFG strength (higher = follow prompt more)     |
| `seed`            | int    | -1      | Random seed (-1 for random)                    |
| `batch_size`      | int    | 1       | Number of variations to generate               |
| `audio_format`    | string | "flac"  | Output format: mp3, wav, flac                  |

### LLM Settings

| Parameter          | Type  | Default | Description                       |
| ------------------ | ----- | ------- | --------------------------------- |
| `thinking`         | bool  | true    | Enable chain-of-thought reasoning |
| `lm_temperature`   | float | 0.85    | LLM creativity (0.0-2.0)          |
| `use_cot_metas`    | bool  | true    | Let LLM detect BPM/key            |
| `use_cot_caption`  | bool  | true    | Let LLM enhance caption           |
| `use_cot_language` | bool  | true    | Let LLM detect language           |

### Advanced

| Parameter     | Type   | Default | Description                                  |
| ------------- | ------ | ------- | -------------------------------------------- |
| `auto_lrc`    | bool   | false   | Generate LRC lyrics timestamps               |
| `use_adg`     | bool   | false   | Adaptive Dual Guidance (base model only)     |
| `shift`       | float  | 1.0     | Timestep shift factor                        |
| `instruction` | string | ""      | Custom instruction (auto-generated if empty) |

### Output Mode (lego/complete tasks)

| Parameter              | Type   | Default | Description                                                |
| ---------------------- | ------ | ------- | ---------------------------------------------------------- |
| `output_mode`          | string | "stems" | `"stems"` = new tracks only, `"mixed"` = mixed with source |
| `mix_volume_source`    | float  | 1.0     | Volume of source audio when mixing (0.0-2.0)               |
| `mix_volume_generated` | float  | 1.0     | Volume of generated audio when mixing (0.0-2.0)            |

---

## Response Format

### Generation Tasks Response

```json
{
  "audios": [
    {
      "url": "https://presigned-s3-url...",
      "key": "sample_0",
      "seed": 12345,
      "sample_rate": 48000,
      "mixed": false // true if output_mode="mixed" was used
    }
  ],
  "audio_url": "https://...", // First audio URL for convenience
  "format": "flac",
  "task_type": "text2music",
  "output_mode": "stems", // "stems" or "mixed"
  "generation_time": 45.2,
  "status_message": "Generation complete",
  "lm_metadata": {
    "bpm": 128,
    "keyscale": "G Major",
    "duration": 120,
    "caption": "Enhanced caption..."
  },
  "lrc": [
    // Only if auto_lrc=true
    {
      "lrc_text": "[00:05.23]Line one\n[00:10.45]Line two",
      "sample_index": 0
    }
  ],
  "time_costs": {
    "lm_total": 5.2,
    "dit_total": 40.0
  }
}
```

### Understand Task Response

```json
{
  "task_type": "understand",
  "caption": "Description of the music...",
  "lyrics": "Extracted lyrics...",
  "bpm": 128,
  "duration": 180.5,
  "keyscale": "C Major",
  "language": "en",
  "timesignature": "4/4",
  "processing_time": 2.5
}
```

### Error Response

```json
{
  "error": "Error message describing what went wrong"
}
```

---

## Track Names

Available track names for `lego`, `extract`, and `complete` tasks:

| Track Name       | Description               |
| ---------------- | ------------------------- |
| `vocals`         | Lead vocals               |
| `backing_vocals` | Background/harmony vocals |
| `drums`          | Drum kit                  |
| `bass`           | Bass guitar/synth bass    |
| `guitar`         | Electric/acoustic guitar  |
| `keyboard`       | Piano, organ, synth pads  |
| `percussion`     | Auxiliary percussion      |
| `strings`        | Orchestral strings        |
| `synth`          | Synthesizers              |
| `fx`             | Sound effects             |
| `brass`          | Brass instruments         |
| `woodwinds`      | Woodwind instruments      |

---

## Model Selection

The model is configured via environment variables on the RunPod endpoint:

| Variable     | Options                                 | Description                                                  |
| ------------ | --------------------------------------- | ------------------------------------------------------------ |
| `DIT_MODEL`  | `acestep-v15-turbo`, `acestep-v15-base` | Turbo (8 steps, fast) or Base (32-100 steps, higher quality) |
| `ENABLE_LLM` | `true`, `false`                         | Enable/disable LLM reasoning                                 |

**Note:** Some tasks (`lego`, `extract`, `complete`) are only available with the Base model.

---

## Examples

### Generate Instrumental Track

```json
{
  "input": {
    "task_type": "text2music",
    "caption": "Cinematic orchestral piece with sweeping strings and epic brass",
    "instrumental": true,
    "duration": 180,
    "batch_size": 2
  }
}
```

### Create Karaoke Version (Remove Vocals)

```json
{
  "input": {
    "task_type": "extract",
    "src_audio": "https://example.com/song.mp3",
    "track_name": "vocals"
  }
}
```

Then subtract the extracted vocals from the original to get instrumental.

### Add Full Band to Vocals (Stems Only)

```json
{
  "input": {
    "task_type": "complete",
    "src_audio": "https://example.com/vocals.mp3",
    "complete_track_classes": [
      "drums",
      "bass",
      "guitar",
      "keyboard",
      "strings"
    ],
    "caption": "Epic pop ballad arrangement with emotional strings and powerful drums"
  }
}
```

### Add Full Band to Vocals (Pre-Mixed Output)

```json
{
  "input": {
    "task_type": "complete",
    "src_audio": "https://example.com/vocals.mp3",
    "complete_track_classes": [
      "drums",
      "bass",
      "guitar",
      "keyboard",
      "strings"
    ],
    "caption": "Epic pop ballad arrangement with emotional strings and powerful drums",
    "output_mode": "mixed",
    "mix_volume_source": 1.0,
    "mix_volume_generated": 0.9
  }
}
```

### Analyze Unknown Song

```json
{
  "input": {
    "task_type": "understand",
    "src_audio": "https://example.com/unknown-song.mp3"
  }
}
```
