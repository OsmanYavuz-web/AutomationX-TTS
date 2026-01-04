"""
AutomationX TTS - API (FastAPI)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import io
import os
import torch
import torchaudio as ta
import random
from datetime import datetime

from core import (
    get_state,
    logger,
    normalize_text,
    AudioProcessor,
    LANGUAGES,
    PRESETS,
    split_into_sentences,
    merge_audio_with_crossfade,
)
from core.cache import model_cache

state = get_state()

api_app = FastAPI(
    title="AutomationX TTS API",
    description="AutomationX TTS Ses Üretim API'si",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

class GenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000, description="Sese dönüştürülecek metin content")
    language: str = Field(default="tr", description="Dil kodu (tr, en, fr, de, es)")
    preset: Optional[str] = Field(default=None, description="Ses şablonu (default, news_anchor, storyteller...)")
    exaggeration: float = Field(default=0.5, ge=0.0, le=2.0, description="Duygu/Vurgu yoğunluğu (0.0 - 2.0)")
    cfg_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Metin takip sadakati (0.0 - 1.0)")
    seed: int = Field(default=-1, description="Rastgelelik tohumu (-1 = rastgele)")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Merhaba, bugün nasılsın? AutomationX TTS ile harika sesler üretebilirsin!",
                "language": "tr",
                "preset": "news_anchor",
                "exaggeration": 0.6,
                "cfg_weight": 0.7,
                "seed": -1
            }
        }

@api_app.post("/unload")
async def api_unload():
    """Modeli bellekten manuel olarak boşaltır."""
    model_cache.clear()
    return {"status": "ok", "message": "Model bellekten boşaltıldı."}

@api_app.get("/health")
async def api_health():
    """Sistem sağlık durumunu ve modelin yüklü olup olmadığını döndürür."""
    is_loaded = model_cache.has("tts")
    
    status = {
        "status": "ok",
        "device": state.device,
        "model_loaded": is_loaded
    }
    
    # Cache timeout bilgisini ekle
    cache_status = model_cache.get_status().get("tts", {})
    if cache_status:
        status["idle_seconds"] = cache_status.get("idle_seconds")
        status["timeout_seconds"] = cache_status.get("timeout_seconds")
        status["remaining_seconds"] = cache_status.get("remaining_seconds")
        
    return status


@api_app.get("/languages")
async def api_languages():
    """Desteklenen dillerin listesini döndürür."""
    return {"languages": {k: v["name_tr"] for k, v in LANGUAGES.items()}}


@api_app.get("/presets")
async def api_presets():
    """Kullanılabilir ses şablonlarını (preset) döndürür."""
    return {"presets": {k: {"name_tr": v["name_tr"], "description": v["description"]} for k, v in PRESETS.items()}}


@api_app.get("/history")
async def api_history(limit: int = 20):
    """Geçmiş üretimleri listeler."""
    return {"history": state.load_history(limit=limit)}


from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
# ... imports

# ... (GenerateRequest class stays for documentation or alternate use, but we need Form params)

@api_app.post("/generate")
async def api_generate(
    text: str = Form(..., description="Sese dönüştürülecek metin"),
    language: str = Form("tr", description="Dil kodu"),
    preset: Optional[str] = Form(None, description="Ses şablonu (Seçilirse alttaki ayarları ezer)"),
    exaggeration: float = Form(0.5, description="Duygu yoğunluğu (Preset boşsa kullanılır)"),
    cfg_weight: float = Form(0.5, description="Sadakat (Preset boşsa kullanılır)"),
    seed: int = Form(-1, description="Seed"),
    ref_audio: Optional[UploadFile] = File(None, description="Referans ses dosyası (Voice Cloning)")
):
    """
    Ses üretimi gerçekleştirir (Multipart Form).
    - **text**: Üretilecek metin
    - **ref_audio**: Referans ses dosyası (WAV/MP3/...)
    """
    try:
        text = text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Metin boş olamaz")
        
        # Preset application logic
        if preset and preset in PRESETS:
            exaggeration = PRESETS[preset]["exaggeration"]
            cfg_weight = PRESETS[preset]["cfg_weight"]
        
        actual_seed = seed if seed >= 0 else random.randint(0, 999999)
        torch.manual_seed(actual_seed)
        
        # Handle Reference Audio
        ref_audio_path = None
        if ref_audio:
            # Save uploaded file temporarily
            temp_dir = os.path.join(state.base_dir, "temp_uploads")
            os.makedirs(temp_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ref_filename = f"upload_{timestamp}_{ref_audio.filename}"
            ref_audio_path = os.path.join(temp_dir, ref_filename)
            
            with open(ref_audio_path, "wb") as buffer:
                content = await ref_audio.read()
                buffer.write(content)
            logger.info(f"[API] Reference audio saved: {ref_audio_path}")

        tts = state.tts_model
        lang_code = language if language in LANGUAGES else "tr"
        
        if lang_code == "tr":
            text = normalize_text(text)
        
        chunks = split_into_sentences(text, max_chars=200)
        logger.info(f"[API] Processing {len(chunks)} chunks...")
        
        audio_segments = []

        for i, chunk in enumerate(chunks):
            chunk_seed = actual_seed + i
            
            # Retry logic
            wav_chunk = None
            for attempt in range(3):
                try:
                    # Set seed per attempt
                    current_seed = chunk_seed + (attempt * 100)
                    torch.manual_seed(current_seed)
                    if torch.cuda.is_available():
                        torch.cuda.manual_seed(current_seed)
                        
                    wav_chunk = tts.generate(
                        chunk, 
                        language_id=lang_code, 
                        audio_prompt_path=ref_audio_path, 
                        exaggeration=exaggeration, 
                        cfg_weight=cfg_weight
                    )
                    break # Success
                except RuntimeError as e:
                    logger.warning(f"[API] Chunk failed (attempt {attempt+1}): {e}")
                    if attempt == 2:
                        logger.error("[API] Skipping chunk after retries.")
                        wav_chunk = torch.zeros(1, int(tts.sr * 0.5))
            
            if wav_chunk is not None:
                audio_segments.append(wav_chunk)
        
        # Clean up uploaded file if needed, or keep for history?
        # For now, let's keep it or maybe a cron job cleans it. 
        # But to prevent disk fill up, maybe clean up after efficient usage?
        # tts.generate loads it. If we return, we can delete it.
        # But let's leave it for now to be safe with async operations or debugging.
        
        if len(audio_segments) > 1:
            wav = merge_audio_with_crossfade(audio_segments, tts.sr)
        else:
            wav = audio_segments[0]
        
        audio_processor = AudioProcessor(state.audio_config)
        wav = audio_processor.process(wav, tts.sr)
        
        os.makedirs(state.outputs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_{timestamp}.wav"
        filepath = os.path.join(state.outputs_dir, filename)
        ta.save(filepath, wav, tts.sr)
        
        state.save_to_history({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "text": text[:500],
            "language": language,
            "seed": actual_seed,
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
            "filename": filename,
        })
        
        duration = wav.shape[1] / tts.sr
        logger.info(f"[API] Generated: {filename}")
        
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        
        # Clean up temp file
        if ref_audio_path and os.path.exists(ref_audio_path):
            try:
                os.remove(ref_audio_path)
                logger.info("[API] Temp reference audio removed.")
            except:
                pass

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"[API] Error: {e}")
        # Clean up temp file in case of error
        if 'ref_audio_path' in locals() and ref_audio_path and os.path.exists(ref_audio_path):
             os.remove(ref_audio_path)
        raise HTTPException(status_code=500, detail=str(e))
