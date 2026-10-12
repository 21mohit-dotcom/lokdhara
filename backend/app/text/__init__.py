"""Pure functions for Mundari, Hindi, and English text (docs/TEXT_PROCESSING_PIPELINE.md).

No database access here, so every rule can be tested on its own. Nothing in this package changes
what a person wrote: unsafe text is rejected, and derived forms are computed alongside it.
"""
