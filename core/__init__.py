"""
AutomationX TTS - Core Module
"""

from .exceptions import (
    TTSError,
    ModelLoadError,
    AudioProcessingError,
    DatabaseError,
    ValidationError,
    error_boundary,
    safe_operation,
    strict_operation,
    logger,
)

from .state import AppState, get_state
from .cache import model_cache
from .normalizer import normalize_text
from .audio_processor import AudioProcessor
from .constants import (
    LANGUAGES, LANGUAGE_CODES, PRESETS, PRESET_KEYS, PRESET_GROUPS,
    get_language_name_tr, get_preset_name_tr, get_language_choices_tr, get_preset_choices_tr
)
from .utils import split_into_sentences, merge_audio_with_crossfade
from . import database

__all__ = [
    # Exceptions
    "TTSError",
    "ModelLoadError",
    "AudioProcessingError",
    "DatabaseError",
    "ValidationError",
    # Decorators
    "error_boundary",
    "safe_operation",
    "strict_operation",
    # State
    "AppState",
    "get_state",
    # Cache
    "model_cache",
    # Normalizer
    "normalize_text",
    # Audio
    "AudioProcessor",
    # Constants
    "LANGUAGES",
    "LANGUAGE_CODES",
    "PRESETS",
    "PRESET_KEYS",
    "PRESET_GROUPS",
    # Helper functions
    "get_language_name_tr",
    "get_preset_name_tr",
    "get_language_choices_tr",
    "get_preset_choices_tr",
    # Utils
    "split_into_sentences",
    "merge_audio_with_crossfade",
    # Database
    "database",
    # Logging
    "logger",
]

