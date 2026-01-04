<div align="center">

# 🎙️ AutomationX TTS

**[Chatterbox TTS](https://github.com/resemble-ai/chatterbox)** motorunu kullanan, production-ready Text-to-Speech servisi.

Yalnızca **3 saniyelik referans ses** ile **sınırsız ses klonlama** yapabilir, **Türkçe dahil 15+ dilde** doğal konuşma üretebilirsiniz. Gradio arayüzü veya REST API ile entegre edin, Docker ile saniyeler içinde deploy edin.

</div>

## ✨ Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🌍 **Çok Dil** | Türkçe, İngilizce, Fransızca, Almanca, İspanyolca... |
| 🎭 **Ses Klonlama** | Referans ses ile konuşma üretimi |
| ⚙️ **Gelişmiş Kontrol** | Duygu yoğunluğu, CFG weight ayarları |
| 📜 **Geçmiş** | Üretimleri kaydet, dinle, ayarları geri yükle |
| 🔌 **REST API** | Swagger dokümantasyonlu tam API |


## 🚀 Hızlı Başlangıç

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


## 🐳 Docker

```bash
# Servisi başlat ve build et
docker-compose up -d --build

# Logları takip et
docker-compose logs -f
```


## ⚙️ Konfigürasyon

`.env.example` → `.env` olarak kopyalayın:

| Değişken | Varsayılan | Açıklama |
|----------|:----------:|----------|
| `HOST` | `0.0.0.0` | Bind adresi |
| `PORT` | `7777` | Sunucu portu |
| `HIGHPASS_FREQ` | `80` | Highpass filtre (Hz) |
| `LOWPASS_FREQ` | `10000` | Lowpass filtre (Hz) |
| `NOISE_GATE_THRESHOLD` | `-45` | Gürültü kapısı (dB) |
| `MAX_CHUNK_CHARS` | `200` | Chunk başına max karakter |
| `SILENCE_BETWEEN_CHUNKS_MS` | `150` | Chunk arası sessizlik (ms) |

### Environment değişikliklerini yaptıktan sonra servisi güncellemek için:

```bash
docker-compose up -d
```

## 📁 Yapı

```
AutomationX-TTS/
├── app.py          # Giriş noktası
├── api/            # FastAPI endpoints
├── ui/             # Gradio arayüz
├── core/           # State, Config, Audio, Utils
└── outputs/        # Üretilen sesler + DB
```


## 🔌 API

`POST /generate` — `multipart/form-data`

```bash
curl -X POST http://localhost:7777/generate \
  -F "text=Merhaba dünya" \
  -F "reference_audio=@voice.wav"
```

---

<div align="center">

**Geliştirici:** Osman Yavuz  
📧 omnyvz.yazilim@gmail.com

</div>