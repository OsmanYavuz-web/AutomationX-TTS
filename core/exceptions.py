"""
AutomationX TTS - Custom Exceptions & Error Handling
"""

import functools
import logging
from typing import Callable, TypeVar, Any

# Logging setup
import os
import logging
from datetime import datetime

# Logging setup
log_handlers = []
log_type = os.getenv("LOG_TYPE", "console").lower()

if "console" in log_type or "both" in log_type:
    log_handlers.append(logging.StreamHandler())

if "file" in log_type or "both" in log_type:
    # Create logs directory
    base_dir = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Generate daily log filename
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(logs_dir, f"app_{today}.log")
    
    log_handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

# Default fallback
if not log_handlers:
    log_handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=log_handlers
)
logger = logging.getLogger("chatterbox")

T = TypeVar("T")


# ===================================================================
# CUSTOM EXCEPTIONS
# ===================================================================

class TTSError(Exception):
    """Base exception for TTS errors"""
    pass


class ModelLoadError(TTSError):
    """Model yüklenirken oluşan hatalar"""
    pass


class AudioProcessingError(TTSError):
    """Ses işleme hatası"""
    pass


class DatabaseError(TTSError):
    """Veritabanı hatası"""
    pass


class ValidationError(TTSError):
    """Girdi doğrulama hatası"""
    pass


# ===================================================================
# ERROR BOUNDARY DECORATOR
# ===================================================================

def error_boundary(
    default_return: Any = None,
    reraise: bool = False,
    log_error: bool = True
) -> Callable:
    """
    Global error boundary decorator.
    Hataları yakalar, loglar ve kullanıcı dostu mesaj döner.
    
    Args:
        default_return: Hata durumunda dönecek değer
        reraise: True ise hatayı tekrar fırlat (Gradio için)
        log_error: Hatayı logla
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except TTSError as e:
                # Validation errors are expected, just warn
                if log_error:
                    logger.warning(f"[{func.__name__}] {e}")
                
                # If reraise is requested (e.g. strict_operation), we must raise it
                if reraise:
                    try:
                        import gradio as gr
                        # Raising gr.Error shows a toast in UI and usually suppresses server traceback
                        raise gr.Error(str(e))
                    except ImportError:
                        # Fallback if gradio not available (e.g. API only)
                        raise e
                return default_return
            except Exception as e:
                # Unexpected errors
                if log_error:
                    logger.error(f"[{func.__name__}] Unexpected error: {e}", exc_info=True)
                if reraise:
                    try:
                         import gradio as gr
                         raise gr.Error(f"Beklenmeyen hata: {str(e)}")
                    except ImportError:
                         raise TTSError(f"Beklenmeyen hata: {str(e)}") from e
                return default_return
        return wrapper
    return decorator


def safe_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Basit error boundary - sadece loglar, default None döner"""
    return error_boundary(default_return=None, reraise=False)(func)


def strict_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Strict error boundary - hatayı wrapper'layıp tekrar fırlatır"""
    return error_boundary(reraise=True)(func)
