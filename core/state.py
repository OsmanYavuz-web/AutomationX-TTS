"""
AutomationX TTS - Application State Management (Singleton)
"""

import os
import torch
from typing import Optional, Any
from dotenv import load_dotenv

from .exceptions import ModelLoadError, logger
from .cache import model_cache
from . import database


class AppState:
    """
    Singleton Application State.
    Tüm global state'i tek noktadan yönetir.
    """
    _instance: Optional["AppState"] = None
    
    def __new__(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Load environment
        load_dotenv()
        
        # Config - General
        self.port = int(os.getenv("PORT", 7860))
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Config - Audio Processing (varsayılanlar .env ile uyumlu)
        self.audio_config = {
            "highpass_freq": int(os.getenv("HIGHPASS_FREQ", 80)),
            "lowpass_freq": int(os.getenv("LOWPASS_FREQ", 10000)),
            "noise_gate_threshold": int(os.getenv("NOISE_GATE_THRESHOLD", -45)),
            "normalize_audio": os.getenv("NORMALIZE_AUDIO", "True").lower() == "true",
        }
        
        # Config - Chunking
        self.max_chunk_chars = int(os.getenv("MAX_CHUNK_CHARS", 200))
        self.silence_between_chunks_ms = int(os.getenv("SILENCE_BETWEEN_CHUNKS_MS", 150))
        self.fade_ms = int(os.getenv("FADE_MS", 30))
        
        # Paths
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.outputs_dir = os.path.join(self.base_dir, "outputs")
        
        # Initialize database
        self.db_path = database.init_database(self.outputs_dir)
        
        self._initialized = True
        logger.info(f"AppState initialized. Device: {self.device}")
    
    # ===================================================================
    # LAZY LOADED MODELS
    # ===================================================================
    
    @property
    def tts_model(self) -> Any:
        """Lazy load TTS model"""
        if not model_cache.has("tts"):
            model_cache.set("tts", self._load_tts_model())
        return model_cache.get("tts")
    
    def _load_tts_model(self) -> Any:
        """TTS modelini yükle"""
        try:
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            
            logger.info("Loading TTS model...")
            
            if self.device == "cpu":
                original_load = torch.load
                torch.load = lambda *args, **kwargs: original_load(
                    *args, **{**kwargs, "map_location": torch.device("cpu")}
                )
            
            model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
            
            if self.device == "cpu":
                torch.load = original_load
            
            logger.info("TTS model loaded successfully.")
            return model
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise ModelLoadError(f"TTS model yüklenemedi: {e}")
    

    # DATABASE OPERATIONS (Delegated)
    # ===================================================================
    
    def save_to_history(self, entry: dict) -> bool:
        """Geçmişe kaydet"""
        return database.add_entry(self.db_path, entry)
    
    def load_history(self, limit: int = 50) -> list:
        """Geçmişi yükle"""
        return database.get_entries(self.db_path, limit)
    
    def get_history_entry(self, filename: str) -> Optional[dict]:
        """Filename ile kayıt bul"""
        return database.get_by_filename(self.db_path, filename)


# Global state instance - import edildiğinde oluşur
def get_state() -> AppState:
    """Get or create AppState singleton"""
    return AppState()
