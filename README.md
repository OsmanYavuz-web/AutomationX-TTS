<div align="center">

# 🎙️ AutomationX TTS

**[Chatterbox TTS](https://github.com/resemble-ai/chatterbox)** motorunu kullanan, production-ready Text-to-Speech servisi.

Yalnızca **3 saniyelik referans ses** ile **sınırsız ses klonlama** yapabilir, **Türkçe dahil 23 dilde** doğal konuşma üretebilirsiniz.

</div>

## ✨ Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🌍 **23 Dil** | Türkçe, İngilizce, Fransızca, Almanca, İspanyolca, Japonca, Çince... |
| 🎭 **Ses Klonlama** | 3 saniyelik referans ses ile voice cloning |
| ⚙️ **Gelişmiş Kontrol** | Duygu yoğunluğu, metin sadakati, seed ayarları |
| 🚀 **Async Job Sistemi** | Uzun metinler için timeout-free işlem |
| 📜 **Geçmiş** | Üretimleri kaydet, dinle, ayarları geri yükle |
| 🔌 **REST API** | Swagger dokümantasyonlu tam API |
| ☁️ **Colab Desteği** | Tek tıkla Google Colab'da çalıştır |


## 🚀 Hızlı Başlangıç

### Lokal Kurulum

```bash
# Klonla
git clone https://github.com/OsmanYavuz-web/AutomationX-TTS
cd AutomationX-TTS

# Sanal ortam
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Kurulum
pip install -r requirements.txt

# Başlat
python app.py
```

**Erişim:**
- 🖥️ UI: `http://localhost:7777`
- 📚 API Docs: `http://localhost:7777/docs`

### Google Colab

1. Colab'ı aç
2. Runtime > Change runtime type > **T4 GPU**
3. Cell 1'i çalıştır (kurulum + restart)
4. Cell 2'yi çalıştır (API başlat)


## 🐳 Docker

```bash
docker-compose up -d --build
docker-compose logs -f
```


## 🔌 API Kullanımı

### Async (Önerilen - Uzun Metinler)

```python
import requests
import time

# 1. Job başlat
response = requests.post("http://localhost:7777/generate/async", data={
    "text": "Uzun metin burada...",
    "language": "tr"
})
job_id = response.json()["job_id"]

# 2. Durumu kontrol et
while True:
    status = requests.get(f"http://localhost:7777/jobs/{job_id}").json()
    print(f"Progress: {status['progress']}%")
    
    if status["status"] == "completed":
        break
    elif status["status"] == "failed":
        raise Exception(status["error"])
    time.sleep(2)

# 3. İndir
audio = requests.get(f"http://localhost:7777/jobs/{job_id}/download")
with open("output.wav", "wb") as f:
    f.write(audio.content)
```

### Sync (Kısa Metinler)

```bash
curl -X POST http://localhost:7777/generate \
  -F "text=Merhaba dünya" \
  -F "language=tr" \
  -o output.wav
```

### Voice Cloning

```bash
curl -X POST http://localhost:7777/generate/async \
  -F "text=Bu klonlanmış sesle üretildi" \
  -F "language=tr" \
  -F "ref_audio=@voice.wav"
```


## 📚 API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/generate/async` | POST | Async ses üretimi başlat (önerilen) |
| `/generate` | POST | Sync ses üretimi |
| `/jobs/{job_id}` | GET | Job durumu sorgula |
| `/jobs/{job_id}/download` | GET | Tamamlanan sesi indir |
| `/health` | GET | Sistem durumu |
| `/languages` | GET | Desteklenen diller |
| `/presets` | GET | Ses şablonları |
| `/unload` | POST | Modeli bellekten kaldır |


## ⚙️ Konfigürasyon

`.env.example` → `.env` olarak kopyalayın:

| Değişken | Varsayılan | Açıklama |
|----------|:----------:|----------|
| `PORT` | `7777` | Sunucu portu |
| `IDLE_TIMEOUT` | `600` | Model idle timeout (sn) |
| `HIGHPASS_FREQ` | `80` | Highpass filtre (Hz) |
| `LOWPASS_FREQ` | `10000` | Lowpass filtre (Hz) |
| `MAX_CHUNK_CHARS` | `200` | Chunk başına max karakter |


## 📁 Yapı

```
AutomationX-TTS/
├── app.py              # Giriş noktası (UI + API)
├── api.py              # FastAPI endpoints + Job sistemi
├── ui.py               # Gradio arayüz
├── core/               # State, Cache, Audio, Utils
├── outputs/            # Üretilen sesler + DB
└── AutomationX_TTS_Colab.ipynb  # Colab notebook
```


## 🌍 Desteklenen Diller

`ar` Arapça • `da` Danca • `de` Almanca • `el` Yunanca • `en` İngilizce • `es` İspanyolca • `fi` Fince • `fr` Fransızca • `he` İbranice • `hi` Hintçe • `it` İtalyanca • `ja` Japonca • `ko` Korece • `ms` Malayca • `nl` Felemenkçe • `no` Norveççe • `pl` Lehçe • `pt` Portekizce • `ru` Rusça • `sv` İsveççe • `sw` Svahili • **`tr` Türkçe** • `zh` Çince

---

<div align="center">

**Geliştirici:** Osman Yavuz  
📧 omnyvz.yazilim@gmail.com

</div>