#!/usr/bin/env python3
"""
Test script for ACE-Step 1.5 RunPod handler.

This script allows testing the handler locally before deploying to RunPod.

Usage:
    # Basic text2music test
    python test_handler_runpod.py --caption "A cinematic orchestral piece with dramatic strings"

    # With lyrics
    python test_handler_runpod.py --caption "Pop song" --lyrics "[Verse 1]\nHello world\nThis is a test"

    # Cover task (requires source audio)
    python test_handler_runpod.py --task cover --caption "Rock version" --src_audio path/to/audio.wav

    # Repaint task
    python test_handler_runpod.py --task repaint --caption "Jazz intro" --src_audio path/to/audio.wav --repainting_start 0 --repainting_end 10
"""
import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser(description="Test ACE-Step 1.5 RunPod handler locally")

    # Task type
    parser.add_argument("--task", type=str, default="text2music",
                       choices=["text2music", "cover", "repaint", "lego", "extract", "complete"],
                       help="Task type")

    # Text inputs
    parser.add_argument("--caption", type=str, default="A cinematic orchestral piece with dramatic strings and percussion",
                       help="Main prompt describing the music")
    parser.add_argument("--lyrics", type=str, default="",
                       help="Lyrics for the music")
    parser.add_argument("--instrumental", action="store_true",
                       help="Force instrumental generation")

    # Music metadata
    parser.add_argument("--duration", type=float, default=-1,
                       help="Target duration in seconds (-1 for auto)")
    parser.add_argument("--bpm", type=int, default=None,
                       help="BPM (None for auto)")
    parser.add_argument("--keyscale", type=str, default="",
                       help="Musical key (e.g., 'C Major')")
    parser.add_argument("--timesignature", type=str, default="",
                       help="Time signature (2, 3, 4, or 6)")
    parser.add_argument("--vocal_language", type=str, default="unknown",
                       help="Vocal language code (en, zh, ja, etc.)")

    # Generation parameters
    parser.add_argument("--inference_steps", type=int, default=8,
                       help="Diffusion steps (8 for turbo, 32-100 for base)")
    parser.add_argument("--guidance_scale", type=float, default=7.0,
                       help="CFG strength")
    parser.add_argument("--seed", type=int, default=-1,
                       help="Seed (-1 for random)")
    parser.add_argument("--batch_size", type=int, default=1,
                       help="Number of samples to generate")
    parser.add_argument("--audio_format", type=str, default="flac",
                       choices=["mp3", "wav", "flac"],
                       help="Output audio format")

    # LLM parameters
    parser.add_argument("--thinking", action="store_true", default=True,
                       help="Enable LLM chain-of-thought reasoning")
    parser.add_argument("--no_thinking", action="store_false", dest="thinking",
                       help="Disable LLM chain-of-thought reasoning")
    parser.add_argument("--lm_temperature", type=float, default=0.85,
                       help="LLM sampling temperature")

    # Audio inputs
    parser.add_argument("--reference_audio", type=str, default=None,
                       help="Path or URL to reference audio (for cover/style transfer)")
    parser.add_argument("--src_audio", type=str, default=None,
                       help="Path or URL to source audio (for repaint/lego/edit)")

    # Repaint parameters
    parser.add_argument("--repainting_start", type=float, default=0.0,
                       help="Start time for repaint region")
    parser.add_argument("--repainting_end", type=float, default=-1,
                       help="End time for repaint region (-1 for end)")
    parser.add_argument("--audio_cover_strength", type=float, default=1.0,
                       help="Reference audio influence (0.0-1.0)")

    args = parser.parse_args()

    # Build input dict
    input_data = {
        "task_type": args.task,
        "caption": args.caption,
        "lyrics": args.lyrics,
        "instrumental": args.instrumental,
        "duration": args.duration,
        "bpm": args.bpm,
        "keyscale": args.keyscale,
        "timesignature": args.timesignature,
        "vocal_language": args.vocal_language,
        "inference_steps": args.inference_steps,
        "guidance_scale": args.guidance_scale,
        "seed": args.seed,
        "batch_size": args.batch_size,
        "audio_format": args.audio_format,
        "thinking": args.thinking,
        "lm_temperature": args.lm_temperature,
        "repainting_start": args.repainting_start,
        "repainting_end": args.repainting_end,
        "audio_cover_strength": args.audio_cover_strength,
    }

    # Handle audio inputs
    if args.reference_audio:
        if os.path.exists(args.reference_audio):
            # It's a local file, read and encode as base64
            import base64
            with open(args.reference_audio, "rb") as f:
                audio_bytes = f.read()
            input_data["reference_audio"] = base64.b64encode(audio_bytes).decode("utf-8")
        else:
            # Assume it's a URL
            input_data["reference_audio"] = args.reference_audio

    if args.src_audio:
        if os.path.exists(args.src_audio):
            # It's a local file, read and encode as base64
            import base64
            with open(args.src_audio, "rb") as f:
                audio_bytes = f.read()
            input_data["src_audio"] = base64.b64encode(audio_bytes).decode("utf-8")
        else:
            # Assume it's a URL
            input_data["src_audio"] = args.src_audio

    # Create event
    event = {"input": input_data}

    print("=" * 60)
    print("Testing ACE-Step 1.5 RunPod Handler")
    print("=" * 60)
    print(f"Input: {json.dumps(input_data, indent=2)}")
    print("=" * 60)

    # Import and call handler
    from handler_runpod import handler

    result = handler(event)

    print("=" * 60)
    print("Result:")
    print("=" * 60)
    print(json.dumps(result, indent=2))

    if "error" in result:
        print(f"\nERROR: {result['error']}")
        return 1

    if "audio_url" in result:
        print(f"\nGenerated audio URL: {result['audio_url']}")

    return 0


if __name__ == "__main__":
    exit(main())
