"""
AutomationX TTS - Model Cache with Idle Timeout
"""

import os
import gc
import time
import threading
from typing import Any, Optional

import torch


class ModelCache:
    """
    Singleton model cache with idle timeout.
    Belirli süre kullanılmayan modeli bellekten kaldırır.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._models = {}
            cls._instance._last_access = {}
            cls._instance._timeout_seconds = int(os.getenv("MODEL_IDLE_TIMEOUT", 600))  # 10 dk default
            cls._instance._cleanup_thread = None
            cls._instance._running = False
        return cls._instance
    
    def get(self, key: str) -> Any:
        """Model al, yoksa None döner. Erişim zamanını günceller."""
        with self._lock:
            if key in self._models:
                self._last_access[key] = time.time()
                return self._models[key]
            return None
    
    def set(self, key: str, model: Any) -> None:
        """Model kaydet ve cleanup thread'i başlat"""
        with self._lock:
            self._models[key] = model
            self._last_access[key] = time.time()
            self._start_cleanup_thread()
    
    def has(self, key: str) -> bool:
        """Model var mı?"""
        return key in self._models
    
    def clear(self, key: str = None) -> None:
        """Cache temizle ve GPU belleği serbest bırak"""
        with self._lock:
            if key:
                if key in self._models:
                    del self._models[key]
                    self._last_access.pop(key, None)
            else:
                self._models.clear()
                self._last_access.clear()
            
            # GPU belleği temizle
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
    
    def _start_cleanup_thread(self) -> None:
        """Cleanup thread'i başlat (eğer çalışmıyorsa)"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_loop(self) -> None:
        """Arka planda idle modelleri kontrol et ve temizle"""
        check_interval = 60  # Her 60 saniyede bir kontrol
        
        while self._running:
            time.sleep(check_interval)
            self._check_and_cleanup()
            
            # Hiç model kalmadıysa thread'i durdur
            if not self._models:
                self._running = False
                break
    
    def _check_and_cleanup(self) -> None:
        """Timeout'a uğramış modelleri temizle"""
        if self._timeout_seconds <= 0:
            return  # Timeout devre dışı
        
        current_time = time.time()
        keys_to_remove = []
        
        with self._lock:
            for key, last_access in self._last_access.items():
                idle_time = current_time - last_access
                if idle_time > self._timeout_seconds:
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            print(f"[ModelCache] '{key}' modeli {self._timeout_seconds}s idle kaldı, bellekten kaldırılıyor...")
            self.clear(key)
    
    def get_status(self) -> dict:
        """Cache durumunu döndür"""
        status = {}
        current_time = time.time()
        
        with self._lock:
            for key in self._models:
                idle_seconds = int(current_time - self._last_access.get(key, current_time))
                remaining = max(0, self._timeout_seconds - idle_seconds)
                status[key] = {
                    "idle_seconds": idle_seconds,
                    "timeout_seconds": self._timeout_seconds,
                    "remaining_seconds": remaining,
                }
        
        return status
    
    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds
    
    @timeout_seconds.setter
    def timeout_seconds(self, value: int) -> None:
        self._timeout_seconds = max(0, value)  # 0 = devre dışı


# Global instance
model_cache = ModelCache()
