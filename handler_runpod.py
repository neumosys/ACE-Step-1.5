"""
RunPod Serverless Handler for ACE-Step 1.5

This handler provides a serverless interface for music generation using
ACE-Step 1.5's DiT model with optional 5Hz LM chain-of-thought reasoning.
"""
import runpod
import os
import base64
import time
import tempfile
import shutil
import uuid
import requests
import boto3
from botocore.config import Config
from botocore.exceptions import NoCredentialsError
from typing import Optional, List, Dict, Any

# Disable tokenizers parallelism to avoid fork warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from loguru import logger

# Initialize handlers globally to load models once
print("Initializing ACE-Step 1.5 handlers...")

# Get configuration from environment
CHECKPOINT_DIR = os.environ.get("CHECKPOINT_DIR", "/app/checkpoints")
DIT_MODEL = os.environ.get("DIT_MODEL", "acestep-v15-turbo")
LM_MODEL = os.environ.get("LM_MODEL", "acestep-5Hz-lm-1.7B")
LM_BACKEND = os.environ.get("LM_BACKEND", "vllm")  # "vllm" or "pt"
DEVICE = os.environ.get("DEVICE", "cuda")
USE_FLASH_ATTENTION = os.environ.get("USE_FLASH_ATTENTION", "true").lower() == "true"
OFFLOAD_TO_CPU = os.environ.get("OFFLOAD_TO_CPU", "false").lower() == "true"

# Initialize DiT handler
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music, understand_music
from acestep.constants import TASK_INSTRUCTIONS, TRACK_NAMES

dit_handler = AceStepHandler()
llm_handler = LLMHandler()

# Initialize DiT model
print(f"Initializing DiT model: {DIT_MODEL}")
status, success = dit_handler.initialize_service(
    project_root=CHECKPOINT_DIR,
    config_path=DIT_MODEL,
    device=DEVICE,
    use_flash_attention=USE_FLASH_ATTENTION,
    compile_model=False,
    offload_to_cpu=OFFLOAD_TO_CPU,
    prefer_source="huggingface",
)
print(f"DiT initialization: {status}")
if not success:
    raise RuntimeError(f"Failed to initialize DiT model: {status}")

# Initialize LLM handler (optional - can be disabled for faster startup)
ENABLE_LLM = os.environ.get("ENABLE_LLM", "true").lower() == "true"
if ENABLE_LLM:
    print(f"Initializing LLM: {LM_MODEL} with backend: {LM_BACKEND}")
    lm_status, lm_success = llm_handler.initialize(
        checkpoint_dir=CHECKPOINT_DIR,
        lm_model_path=LM_MODEL,
        backend=LM_BACKEND,
        device=DEVICE,
        offload_to_cpu=OFFLOAD_TO_CPU,
    )
    print(f"LLM initialization: {lm_status}")
    if not lm_success:
        print(f"WARNING: LLM initialization failed, running in DiT-only mode")
        ENABLE_LLM = False
else:
    print("LLM disabled - running in DiT-only mode")

print("ACE-Step 1.5 handlers initialized.")

# Initialize S3 Client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    config=Config(signature_version='s3v4')
)
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")


def upload_to_s3(file_path: str, bucket: str, object_name: Optional[str] = None) -> Optional[str]:
    """Upload a file to S3 and return a presigned URL."""
    if object_name is None:
        object_name = os.path.basename(file_path)

    try:
        s3_client.upload_file(file_path, bucket, object_name)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': object_name},
            ExpiresIn=3600 * 24  # 24 hours
        )
        return url
    except FileNotFoundError:
        logger.error("File not found for S3 upload")
        return None
    except NoCredentialsError:
        logger.error("AWS credentials not available")
        return None
    except Exception as e:
        logger.error(f"Error uploading to S3: {e}")
        return None


def generate_instruction(
    task_type: str,
    track_name: Optional[str] = None,
    complete_track_classes: Optional[List[str]] = None
) -> str:
    """Generate the appropriate instruction based on task type and parameters."""
    if task_type == "text2music":
        return TASK_INSTRUCTIONS["text2music"]
    elif task_type == "repaint":
        return TASK_INSTRUCTIONS["repaint"]
    elif task_type == "cover":
        return TASK_INSTRUCTIONS["cover"]
    elif task_type == "extract":
        if track_name:
            return TASK_INSTRUCTIONS["extract"].format(TRACK_NAME=track_name.upper())
        else:
            return TASK_INSTRUCTIONS["extract_default"]
    elif task_type == "lego":
        if track_name:
            return TASK_INSTRUCTIONS["lego"].format(TRACK_NAME=track_name.upper())
        else:
            return TASK_INSTRUCTIONS["lego_default"]
    elif task_type == "complete":
        if complete_track_classes and len(complete_track_classes) > 0:
            track_classes_str = " | ".join(t.upper() for t in complete_track_classes)
            return TASK_INSTRUCTIONS["complete"].format(TRACK_CLASSES=track_classes_str)
        else:
            return TASK_INSTRUCTIONS["complete_default"]
    else:
        return TASK_INSTRUCTIONS["text2music"]


def mix_audio_files(source_path: str, generated_path: str, output_path: str, source_volume: float = 1.0, generated_volume: float = 1.0) -> bool:
    """
    Mix source audio with generated audio using ffmpeg.

    Args:
        source_path: Path to original/source audio file
        generated_path: Path to generated audio file
        output_path: Path for mixed output
        source_volume: Volume multiplier for source (1.0 = original)
        generated_volume: Volume multiplier for generated (1.0 = original)

    Returns:
        True if successful, False otherwise
    """
    import subprocess

    try:
        # Use ffmpeg to mix two audio files
        # amix filter combines audio streams, duration=longest ensures full length
        cmd = [
            'ffmpeg', '-y',
            '-i', source_path,
            '-i', generated_path,
            '-filter_complex',
            f'[0:a]volume={source_volume}[a0];[1:a]volume={generated_volume}[a1];[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0',
            '-ac', '2',  # Stereo output
            '-ar', '48000',  # 48kHz sample rate
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            logger.error(f"ffmpeg mixing failed: {result.stderr}")
            return False

        return True

    except subprocess.TimeoutExpired:
        logger.error("ffmpeg mixing timed out")
        return False
    except Exception as e:
        logger.error(f"Error mixing audio: {e}")
        return False


def download_or_decode_audio(input_str: str, suffix: str = ".wav") -> Optional[str]:
    """
    Decode base64 string OR download from URL to a temporary file.
    Returns the path to the temporary file.
    """
    if not input_str:
        return None

    path = None
    try:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)

        # Check if it's a URL
        if input_str.startswith("http://") or input_str.startswith("https://"):
            logger.info(f"Downloading audio from URL: {input_str}")
            response = requests.get(input_str, stream=True, timeout=60)
            response.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            # Assume base64
            # Handle data URI scheme if present
            if "," in input_str:
                input_str = input_str.split(",")[1]

            audio_bytes = base64.b64decode(input_str)
            with open(path, 'wb') as f:
                f.write(audio_bytes)

        return path
    except Exception as e:
        logger.error(f"Error processing audio input: {e}")
        if path and os.path.exists(path):
            os.remove(path)
        return None


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler function for ACE-Step 1.5.

    Input parameters:
    - task_type: str = "text2music" (text2music, cover, repaint, lego, extract, complete, understand)
    - caption: str = "" (main prompt describing the music)
    - lyrics: str = "" (lyrics for the music, use "[Instrumental]" for instrumental)
    - instrumental: bool = False (force instrumental generation)
    - duration: float = -1 (target duration in seconds, -1 for auto)
    - bpm: int = None (beats per minute, None for auto)
    - keyscale: str = "" (musical key, e.g., "C Major", empty for auto)
    - timesignature: str = "" (time signature: 2, 3, 4, or 6)
    - vocal_language: str = "unknown" (language code: en, zh, ja, etc.)
    - inference_steps: int = 8 (diffusion steps, 8 for turbo, 32-100 for base)
    - guidance_scale: float = 7.0 (CFG strength)
    - seed: int = -1 (-1 for random)
    - batch_size: int = 1 (number of samples to generate)
    - audio_format: str = "flac" (output format: mp3, wav, flac)
    - thinking: bool = True (enable LLM chain-of-thought reasoning)
    - lm_temperature: float = 0.85 (LLM sampling temperature)
    - reference_audio: str = None (URL or base64 for cover/style transfer)
    - src_audio: str = None (URL or base64 for repaint/lego/extract/complete tasks)
    - audio_codes: str = "" (pre-computed audio codes, for understand task or advanced use)
    - repainting_start: float = 0.0 (start time for repaint/lego region)
    - repainting_end: float = -1 (end time for repaint/lego region, -1 for end)
    - audio_cover_strength: float = 1.0 (reference audio influence, 0.0-1.0)
    - track_name: str = None (for lego/extract tasks: vocals, drums, bass, guitar, keyboard, etc.)
    - complete_track_classes: list = [] (for complete task: list of tracks to add, e.g., ["drums", "bass", "guitar"])
    - auto_lrc: bool = False (generate LRC lyrics timestamps after generation)
    - output_mode: str = "stems" (for lego/complete: "stems" returns new tracks only, "mixed" returns mixed with source)
    - mix_volume_source: float = 1.0 (volume of source audio when mixing, 0.0-2.0)
    - mix_volume_generated: float = 1.0 (volume of generated audio when mixing, 0.0-2.0)

    Available track names for lego/extract/complete:
    vocals, backing_vocals, drums, bass, guitar, keyboard, percussion, strings, synth, fx, brass, woodwinds

    Task type "understand": Analyzes audio and extracts metadata (caption, lyrics, bpm, key, etc.)
    - Accepts src_audio (URL or base64) which gets converted to audio codes internally
    - Or accepts raw audio_codes directly (advanced use)
    - Returns: caption, lyrics, bpm, duration, keyscale, language, timesignature
    """
    logger.info(f"Received event: {event}")
    job_input = event.get("input", {})

    # Check for S3 configuration
    if not S3_BUCKET_NAME:
        return {"error": "S3_BUCKET_NAME environment variable is not set."}

    # Create a temporary directory for this job
    job_dir = tempfile.mkdtemp()
    output_dir = os.path.join(job_dir, "outputs")
    os.makedirs(output_dir, exist_ok=True)

    temp_files = []

    try:
        # --- Extract Parameters ---
        # Task type
        task_type = job_input.get("task_type", "text2music")

        # Text inputs
        caption = job_input.get("caption", "")
        lyrics = job_input.get("lyrics", "")
        instrumental = job_input.get("instrumental", False)

        # Music metadata
        duration = float(job_input.get("duration", -1))
        bpm = job_input.get("bpm")
        if bpm is not None:
            bpm = int(bpm)
        keyscale = job_input.get("keyscale", "")
        timesignature = job_input.get("timesignature", "")
        vocal_language = job_input.get("vocal_language", "unknown")

        # Generation parameters
        inference_steps = int(job_input.get("inference_steps", 8))
        guidance_scale = float(job_input.get("guidance_scale", 7.0))
        seed = int(job_input.get("seed", -1))
        batch_size = int(job_input.get("batch_size", 1))
        audio_format = job_input.get("audio_format", "flac")

        # LLM parameters
        thinking = job_input.get("thinking", True) if ENABLE_LLM else False
        lm_temperature = float(job_input.get("lm_temperature", 0.85))
        lm_cfg_scale = float(job_input.get("lm_cfg_scale", 2.0))
        use_cot_metas = job_input.get("use_cot_metas", True)
        use_cot_caption = job_input.get("use_cot_caption", True)
        use_cot_language = job_input.get("use_cot_language", True)

        # Advanced DiT parameters
        use_adg = job_input.get("use_adg", False)
        cfg_interval_start = float(job_input.get("cfg_interval_start", 0.0))
        cfg_interval_end = float(job_input.get("cfg_interval_end", 1.0))
        shift = float(job_input.get("shift", 1.0))

        # Audio codes (advanced)
        audio_codes = job_input.get("audio_codes", "")

        # Reference audio (for cover/style transfer)
        reference_audio_str = job_input.get("reference_audio")
        reference_audio = None
        if reference_audio_str:
            reference_audio = download_or_decode_audio(reference_audio_str)
            if reference_audio:
                temp_files.append(reference_audio)

        # Source audio (for repaint/lego/edit tasks)
        src_audio_str = job_input.get("src_audio")
        src_audio = None
        if src_audio_str:
            src_audio = download_or_decode_audio(src_audio_str)
            if src_audio:
                temp_files.append(src_audio)

        # Repaint/lego parameters
        repainting_start = float(job_input.get("repainting_start", 0.0))
        repainting_end = float(job_input.get("repainting_end", -1))
        audio_cover_strength = float(job_input.get("audio_cover_strength", 1.0))

        # Task-specific parameters for lego/extract/complete
        track_name = job_input.get("track_name")
        complete_track_classes = job_input.get("complete_track_classes", [])

        # Auto LRC generation
        auto_lrc = job_input.get("auto_lrc", False)

        # Output mode for lego/complete tasks
        output_mode = job_input.get("output_mode", "stems")  # "stems" or "mixed"
        mix_volume_source = float(job_input.get("mix_volume_source", 1.0))
        mix_volume_generated = float(job_input.get("mix_volume_generated", 1.0))

        # Instruction - generate based on task type if not provided
        instruction = job_input.get("instruction", "")
        if not instruction:
            instruction = generate_instruction(task_type, track_name, complete_track_classes)

        # Validation
        if task_type in ["cover", "repaint", "lego", "extract", "complete"] and not src_audio and not reference_audio:
            return {"error": f"Task '{task_type}' requires 'src_audio' or 'reference_audio'."}

        # Handle understand task separately (no audio generation)
        if task_type == "understand":
            if not ENABLE_LLM:
                return {"error": "Understand task requires LLM to be enabled"}

            # Get audio codes - either from direct input or by converting src_audio
            codes_to_understand = audio_codes
            if not codes_to_understand and src_audio:
                logger.info("Converting src_audio to audio codes for understanding...")
                codes_to_understand = dit_handler.convert_src_audio_to_codes(src_audio)
                if codes_to_understand.startswith("❌"):
                    return {"error": f"Failed to convert audio to codes: {codes_to_understand}"}

            if not codes_to_understand:
                return {"error": "Understand task requires 'src_audio' or 'audio_codes' parameter"}

            logger.info("Starting understand task")
            start_time = time.time()

            result = understand_music(
                llm_handler=llm_handler,
                audio_codes=codes_to_understand,
                temperature=lm_temperature,
            )

            end_time = time.time()

            if not result.success:
                return {"error": result.error or "Understand task failed"}

            return {
                "task_type": "understand",
                "caption": result.caption,
                "lyrics": result.lyrics,
                "bpm": result.bpm,
                "duration": result.duration,
                "keyscale": result.keyscale,
                "language": result.language,
                "timesignature": result.timesignature,
                "status_message": result.status_message,
                "processing_time": end_time - start_time,
            }

        logger.info(f"Starting generation for task: {task_type}")
        start_time = time.time()

        # Build GenerationParams
        params = GenerationParams(
            task_type=task_type,
            caption=caption,
            lyrics=lyrics,
            instrumental=instrumental,
            duration=duration,
            bpm=bpm,
            keyscale=keyscale,
            timesignature=timesignature,
            vocal_language=vocal_language,
            inference_steps=inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
            thinking=thinking,
            lm_temperature=lm_temperature,
            lm_cfg_scale=lm_cfg_scale,
            use_cot_metas=use_cot_metas,
            use_cot_caption=use_cot_caption,
            use_cot_language=use_cot_language,
            use_adg=use_adg,
            cfg_interval_start=cfg_interval_start,
            cfg_interval_end=cfg_interval_end,
            shift=shift,
            audio_codes=audio_codes,
            reference_audio=reference_audio,
            src_audio=src_audio,
            repainting_start=repainting_start,
            repainting_end=repainting_end,
            audio_cover_strength=audio_cover_strength,
            instruction=instruction,
        )

        # Build GenerationConfig
        config = GenerationConfig(
            batch_size=batch_size,
            audio_format=audio_format,
            use_random_seed=(seed == -1),
            seeds=[seed] if seed != -1 else None,
        )

        # Generate music
        result = generate_music(
            dit_handler=dit_handler,
            llm_handler=llm_handler if ENABLE_LLM else None,
            params=params,
            config=config,
            save_dir=output_dir,
        )

        end_time = time.time()
        generation_time = end_time - start_time
        logger.info(f"Generation completed in {generation_time:.2f} seconds.")

        # Check for errors
        if not result.success:
            return {"error": result.error or "Generation failed"}

        if not result.audios:
            return {"error": "No audio generated"}

        # Mix with source audio if requested (for lego/complete tasks)
        should_mix = (
            output_mode == "mixed" and
            task_type in ["lego", "complete"] and
            src_audio is not None
        )

        if should_mix:
            logger.info(f"Mixing generated audio with source (volumes: source={mix_volume_source}, generated={mix_volume_generated})")

        # Upload results to S3
        audio_urls = []
        for idx, audio in enumerate(result.audios):
            audio_path = audio.get("path")
            if audio_path and os.path.exists(audio_path):
                upload_path = audio_path

                # Mix with source if requested
                if should_mix:
                    mixed_path = os.path.join(output_dir, f"mixed_{idx}.{audio_format}")
                    if mix_audio_files(src_audio, audio_path, mixed_path, mix_volume_source, mix_volume_generated):
                        upload_path = mixed_path
                        temp_files.append(mixed_path)
                        logger.info(f"Successfully mixed audio {idx}")
                    else:
                        logger.warning(f"Mixing failed for audio {idx}, uploading unmixed version")

                file_name = f"{uuid.uuid4()}.{audio_format}"
                s3_url = upload_to_s3(upload_path, S3_BUCKET_NAME, file_name)
                if s3_url:
                    audio_urls.append({
                        "url": s3_url,
                        "key": audio.get("key"),
                        "seed": audio.get("params", {}).get("seed"),
                        "sample_rate": audio.get("sample_rate", 48000),
                        "mixed": should_mix and upload_path != audio_path,
                    })

        if not audio_urls:
            return {"error": "Failed to upload to S3"}

        # Generate LRC timestamps if requested
        lrc_results = []
        if auto_lrc and not instrumental:
            extra_outputs = result.extra_outputs
            pred_latents = extra_outputs.get("pred_latents")
            encoder_hidden_states = extra_outputs.get("encoder_hidden_states")
            encoder_attention_mask = extra_outputs.get("encoder_attention_mask")
            context_latents = extra_outputs.get("context_latents")
            lyric_token_idss = extra_outputs.get("lyric_token_idss")

            if all(x is not None for x in [pred_latents, encoder_hidden_states, encoder_attention_mask, context_latents, lyric_token_idss]):
                import torch
                # Move tensors to device if needed
                device = dit_handler.device if hasattr(dit_handler, 'device') else 'cuda'

                for i in range(min(batch_size, pred_latents.shape[0])):
                    try:
                        # Calculate duration from latents (25 Hz latent rate)
                        latent_length = pred_latents.shape[1]
                        audio_duration = latent_length / 25.0

                        # Get sample data
                        sample_pred_latent = pred_latents[i:i+1].to(device)
                        sample_encoder_hidden_states = encoder_hidden_states[i:i+1].to(device)
                        sample_encoder_attention_mask = encoder_attention_mask[i:i+1].to(device)
                        sample_context_latents = context_latents[i:i+1].to(device)
                        sample_lyric_token_ids = lyric_token_idss[i:i+1].to(device)

                        lrc_result = dit_handler.get_lyric_timestamp(
                            pred_latent=sample_pred_latent,
                            encoder_hidden_states=sample_encoder_hidden_states,
                            encoder_attention_mask=sample_encoder_attention_mask,
                            context_latents=sample_context_latents,
                            lyric_token_ids=sample_lyric_token_ids,
                            total_duration_seconds=float(audio_duration),
                            vocal_language=vocal_language or "en",
                            inference_steps=int(inference_steps),
                            seed=42,
                        )

                        if lrc_result.get("success"):
                            lrc_results.append({
                                "lrc_text": lrc_result.get("lrc_text", ""),
                                "sample_index": i,
                            })
                        else:
                            lrc_results.append({
                                "error": lrc_result.get("error", "Unknown error"),
                                "sample_index": i,
                            })
                    except Exception as e:
                        logger.warning(f"Failed to generate LRC for sample {i}: {e}")
                        lrc_results.append({
                            "error": str(e),
                            "sample_index": i,
                        })
            else:
                logger.warning("LRC generation requested but required tensors not available")

        # Build response
        response = {
            "audios": audio_urls,
            "audio_url": audio_urls[0]["url"],  # Primary audio for backwards compatibility
            "format": audio_format,
            "task_type": task_type,
            "generation_time": generation_time,
            "status_message": result.status_message,
            "output_mode": "mixed" if should_mix else "stems",
        }

        # Add LRC results if generated
        if lrc_results:
            response["lrc"] = lrc_results

        # Add metadata from LLM if available
        if result.extra_outputs.get("lm_metadata"):
            response["lm_metadata"] = result.extra_outputs["lm_metadata"]

        # Add time costs
        if result.extra_outputs.get("time_costs"):
            response["time_costs"] = result.extra_outputs["time_costs"]

        return response

    except Exception as e:
        logger.exception(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    finally:
        # Cleanup temp files and directories
        for p in temp_files:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass
        if os.path.exists(job_dir):
            try:
                shutil.rmtree(job_dir)
            except:
                pass


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
