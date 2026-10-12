"""Audio checks run by the worker (docs/AUDIO_PROCESSING_PIPELINE.md).

`ffmpeg` runs the external tools on untrusted files; the other modules are pure functions over
what the tools report, so every rule can be tested without audio.
"""
