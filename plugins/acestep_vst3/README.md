# ACE-Step VST3 Shell

This directory contains the isolated JUCE/CMake scaffold for the ACE-Step VST3 MVP shell.

What it includes:

- a VST3-only JUCE plugin target
- placeholder editor UI
- versioned plugin state persistence
- no backend or generation calls yet

## Build

Requirements:

- CMake 3.22 or newer
- a C++20-capable compiler
- Git access to fetch JUCE during configure

Configure and build:

```bash
cmake -S plugins/acestep_vst3 -B build/acestep_vst3
cmake --build build/acestep_vst3 --config Release
```

On Windows, use Visual Studio 2022 or the Ninja generator. On macOS, Xcode or Ninja both work.

The first configure step downloads JUCE from GitHub. If you need to work offline later, vendor or
pin JUCE locally before widening the scope of this plugin.

## Validate

The current shell is intentionally minimal. Manual validation should focus on:

- plugin loads in Reaper on Windows
- plugin loads in Reaper on macOS
- editor opens and closes cleanly
- state survives save and reopen

There is no backend integration in this milestone.
