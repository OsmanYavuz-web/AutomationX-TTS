"""
AutomationX TTS - API (FastAPI) with Background Job System
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict
import io
import os
import torch
import torchaudio as ta
import random
import uuid
import threading
import time
from datetime import datetime
from enum import Enum

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

# ===================================================================
# JOB QUEUE SYSTEM
# ===================================================================

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Job:
    def __init__(self, job_id: str, params: dict):
        self.id = job_id
        self.status = JobStatus.PENDING
        self.params = params
        self.result_path: Optional[str] = None
        self.error: Optional[str] = None
        self.progress: float = 0.0
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None

# In-memory job store (Colab için yeterli)
jobs: Dict[str, Job] = {}
job_lock = threading.Lock()

def cleanup_old_jobs():
    """1 saatten eski job'ları temizle"""
    with job_lock:
        now = datetime.now()
        to_delete = []
        for job_id, job in jobs.items():
            age = (now - job.created_at).total_seconds()
            if age > 3600:  # 1 saat
                to_delete.append(job_id)
                # Dosyayı da sil
                if job.result_path and os.path.exists(job.result_path):
                    try:
                        os.remove(job.result_path)
                    except:
                        pass
        for job_id in to_delete:
            del jobs[job_id]

def process_tts_job(job: Job):
    """Arka planda TTS işlemi"""
    try:
        job.status = JobStatus.PROCESSING
        params = job.params
        
        text = params["text"].strip()
        language = params.get("language", "tr")
        preset = params.get("preset")
        exaggeration = params.get("exaggeration", 0.5)
        cfg_weight = params.get("cfg_weight", 0.5)
        seed = params.get("seed", -1)
        ref_audio_path = params.get("ref_audio_path")
        
        # Preset uygula
        if preset and preset in PRESETS:
            exaggeration = PRESETS[preset]["exaggeration"]
            cfg_weight = PRESETS[preset]["cfg_weight"]
        
        actual_seed = seed if seed >= 0 else random.randint(0, 999999)
        torch.manual_seed(actual_seed)
        
        tts = state.tts_model
        lang_code = language if language in LANGUAGES else "tr"
        
        if lang_code == "tr":
            text = normalize_text(text)
        
        chunks = split_into_sentences(text, max_chars=200)
        total_chunks = len(chunks)
        logger.info(f"[Job {job.id}] Processing {total_chunks} chunks...")
        
        audio_segments = []
        
        for i, chunk in enumerate(chunks):
            job.progress = (i / total_chunks) * 0.8  # 0-80%
            chunk_seed = actual_seed + i
            
            wav_chunk = None
            for attempt in range(3):
                try:
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
                    break
                except RuntimeError as e:
                    logger.warning(f"[Job {job.id}] Chunk failed (attempt {attempt+1}): {e}")
                    if attempt == 2:
                        wav_chunk = torch.zeros(1, int(tts.sr * 0.5))
            
            if wav_chunk is not None:
                audio_segments.append(wav_chunk)
        
        job.progress = 0.85
        
        if len(audio_segments) > 1:
            wav = merge_audio_with_crossfade(audio_segments, tts.sr)
        else:
            wav = audio_segments[0]
        
        job.progress = 0.9
        
        audio_processor = AudioProcessor(state.audio_config)
        wav = audio_processor.process(wav, tts.sr)
        
        # Kaydet
        os.makedirs(state.outputs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"job_{job.id}_{timestamp}.wav"
        filepath = os.path.join(state.outputs_dir, filename)
        ta.save(filepath, wav, tts.sr)
        
        job.result_path = filepath
        job.status = JobStatus.COMPLETED
        job.progress = 1.0
        job.completed_at = datetime.now()
        
        logger.info(f"[Job {job.id}] Completed: {filename}")
        
        # Temp ref audio temizle
        if ref_audio_path and os.path.exists(ref_audio_path):
            try:
                os.remove(ref_audio_path)
            except:
                pass
        
        # Eski job'ları temizle
        cleanup_old_jobs()
        
    except Exception as e:
        logger.error(f"[Job {job.id}] Failed: {e}")
        job.status = JobStatus.FAILED
        job.error = str(e)


# ===================================================================
# API
# ===================================================================

# OpenAPI Tags
tags_metadata = [
    {
        "name": "🎤 Ses Üretimi",
        "description": "Text-to-Speech ses üretim endpoint'leri. Async (önerilen) veya Sync modda çalışır.",
    },
    {
        "name": "📋 Job Yönetimi",
        "description": "Async job'ların durumunu sorgulama ve sonuçları indirme.",
    },
    {
        "name": "⚙️ Sistem",
        "description": "Sağlık kontrolü, model yönetimi ve konfigürasyon.",
    },
]

api_app = FastAPI(
    title="AutomationX TTS API",
    description="""
## 🎙️ AutomationX TTS - Chatterbox Multilingual TTS API

**23 dil destekli** yüksek kaliteli ses üretim API'si.

### 🚀 Hızlı Başlangıç

**Async (Önerilen - Uzun metinler için):**
1. `POST /generate/async` → `job_id` alın
2. `GET /jobs/{job_id}` → Durumu kontrol edin
3. `GET /jobs/{job_id}/download` → Sesi indirin

**Sync (Kısa metinler için):**
- `POST /generate` → Direkt WAV döner

### 🌍 Desteklenen Diller
ar, da, de, el, en, es, fi, fr, he, hi, it, ja, ko, ms, nl, no, pl, pt, ru, sv, sw, **tr**, zh

### 🎭 Voice Cloning
Referans ses dosyası yükleyerek kendi sesinizi klonlayabilirsiniz.
""",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
)

@api_app.post("/unload", tags=["⚙️ Sistem"], summary="Modeli Boşalt")
async def api_unload():
    """
    TTS modelini GPU/CPU belleğinden kaldırır.
    
    Sonraki istekte model otomatik tekrar yüklenir.
    """
    model_cache.clear()
    return {"status": "ok", "message": "Model bellekten boşaltıldı."}

@api_app.get("/health", tags=["⚙️ Sistem"], summary="Sağlık Kontrolü")
async def api_health():
    """Sistem sağlık durumu"""
    is_loaded = model_cache.has("tts")
    pending_jobs = sum(1 for j in jobs.values() if j.status == JobStatus.PENDING)
    processing_jobs = sum(1 for j in jobs.values() if j.status == JobStatus.PROCESSING)
    
    return {
        "status": "ok",
        "device": state.device,
        "model_loaded": is_loaded,
        "pending_jobs": pending_jobs,
        "processing_jobs": processing_jobs,
    }

@api_app.get("/languages", tags=["⚙️ Sistem"], summary="Dil Listesi")
async def api_languages():
    """Desteklenen 23 dilin listesini döndürür."""
    return {"languages": {k: v["name_tr"] for k, v in LANGUAGES.items()}}

@api_app.get("/presets", tags=["⚙️ Sistem"], summary="Ses Şablonları")
async def api_presets():
    """Hazır ses şablonlarını listeler (news_anchor, storyteller, vb.)."""
    return {"presets": {k: {"name_tr": v["name_tr"], "description": v["description"]} for k, v in PRESETS.items()}}


# ===================================================================
# ASYNC GENERATE (Yeni - Önerilen)
# ===================================================================

@api_app.post("/generate/async", tags=["🎤 Ses Üretimi"], summary="Async Ses Üret (Önerilen)")
async def api_generate_async(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="Sese dönüştürülecek metin (max 50.000 karakter)"),
    language: str = Form("tr", description="Dil kodu (tr, en, de, fr, ...)"),
    preset: Optional[str] = Form(None, description="Ses şablonu (default, news_anchor, storyteller...)"),
    exaggeration: float = Form(0.5, description="Duygu yoğunluğu (0.0 - 2.0)"),
    cfg_weight: float = Form(0.5, description="Metin sadakati (0.0 - 1.0)"),
    seed: int = Form(-1, description="Rastgelelik tohumu (-1 = rastgele)"),
    ref_audio: Optional[UploadFile] = File(None, description="Voice cloning için referans ses (WAV/MP3)")
):
    """
    Async ses üretimi başlatır. Hemen job_id döner.
    Sonucu almak için: GET /jobs/{job_id}
    Dosyayı indirmek için: GET /jobs/{job_id}/download
    """
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Metin boş olamaz")
    
    # Job oluştur
    job_id = str(uuid.uuid4())[:8]
    
    # Ref audio varsa kaydet
    ref_audio_path = None
    if ref_audio:
        temp_dir = os.path.join(state.base_dir, "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        ref_audio_path = os.path.join(temp_dir, f"{job_id}_{ref_audio.filename}")
        with open(ref_audio_path, "wb") as f:
            content = await ref_audio.read()
            f.write(content)
    
    job = Job(job_id, {
        "text": text,
        "language": language,
        "preset": preset,
        "exaggeration": exaggeration,
        "cfg_weight": cfg_weight,
        "seed": seed,
        "ref_audio_path": ref_audio_path,
    })
    
    with job_lock:
        jobs[job_id] = job
    
    # Arka planda işle
    background_tasks.add_task(process_tts_job, job)
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Job başlatıldı. Durumu kontrol etmek için: GET /jobs/{job_id}"
    }


@api_app.get("/jobs/{job_id}", tags=["📋 Job Yönetimi"], summary="Job Durumu")
async def api_job_status(job_id: str):
    """
    Job'un mevcut durumunu sorgular.
    
    **Durumlar:**
    - `pending`: Kuyrukta bekliyor
    - `processing`: İşleniyor (progress ile takip edin)
    - `completed`: Tamamlandı (download_url mevcut)
    - `failed`: Hata oluştu (error mesajı mevcut)
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    
    response = {
        "job_id": job.id,
        "status": job.status.value,
        "progress": round(job.progress * 100, 1),
    }
    
    if job.status == JobStatus.COMPLETED:
        response["download_url"] = f"/jobs/{job_id}/download"
    elif job.status == JobStatus.FAILED:
        response["error"] = job.error
    
    return response


@api_app.get("/jobs/{job_id}/download", tags=["📋 Job Yönetimi"], summary="Ses Dosyasını İndir")
async def api_job_download(job_id: str):
    """
    Tamamlanan job'un üretilen ses dosyasını indirir (WAV formatı).
    
    Job durumu `completed` olmalıdır.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job henüz tamamlanmadı. Durum: {job.status.value}")
    
    if not job.result_path or not os.path.exists(job.result_path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    
    return FileResponse(
        job.result_path,
        media_type="audio/wav",
        filename=os.path.basename(job.result_path)
    )


# ===================================================================
# SYNC GENERATE (Eski - Kısa metinler için)
# ===================================================================

@api_app.post("/generate", tags=["🎤 Ses Üretimi"], summary="Sync Ses Üret (Kısa Metinler)")
async def api_generate(
    text: str = Form(..., description="Sese dönüştürülecek metin"),
    language: str = Form("tr", description="Dil kodu (tr, en, de, fr, ...)"),
    preset: Optional[str] = Form(None, description="Ses şablonu"),
    exaggeration: float = Form(0.5, description="Duygu yoğunluğu (0.0 - 2.0)"),
    cfg_weight: float = Form(0.5, description="Metin sadakati (0.0 - 1.0)"),
    seed: int = Form(-1, description="Rastgelelik tohumu (-1 = rastgele)"),
    ref_audio: Optional[UploadFile] = File(None, description="Voice cloning için referans ses")
):
    """
    Senkron ses üretimi (kısa metinler için).
    Uzun metinlerde timeout riski var, /generate/async kullanın.
    """
    try:
        text = text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Metin boş olamaz")
        
        if preset and preset in PRESETS:
            exaggeration = PRESETS[preset]["exaggeration"]
            cfg_weight = PRESETS[preset]["cfg_weight"]
        
        actual_seed = seed if seed >= 0 else random.randint(0, 999999)
        torch.manual_seed(actual_seed)
        
        ref_audio_path = None
        if ref_audio:
            temp_dir = os.path.join(state.base_dir, "temp_uploads")
            os.makedirs(temp_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ref_audio_path = os.path.join(temp_dir, f"upload_{timestamp}_{ref_audio.filename}")
            with open(ref_audio_path, "wb") as f:
                content = await ref_audio.read()
                f.write(content)

        tts = state.tts_model
        lang_code = language if language in LANGUAGES else "tr"
        
        if lang_code == "tr":
            text = normalize_text(text)
        
        chunks = split_into_sentences(text, max_chars=200)
        audio_segments = []

        for i, chunk in enumerate(chunks):
            chunk_seed = actual_seed + i
            wav_chunk = None
            
            for attempt in range(3):
                try:
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
                    break
                except RuntimeError as e:
                    if attempt == 2:
                        wav_chunk = torch.zeros(1, int(tts.sr * 0.5))
            
            if wav_chunk is not None:
                audio_segments.append(wav_chunk)
        
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
        
        # Cleanup
        if ref_audio_path and os.path.exists(ref_audio_path):
            try:
                os.remove(ref_audio_path)
            except:
                pass

        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"[API] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
