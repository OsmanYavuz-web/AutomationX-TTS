"""
AutomationX TTS - Constants
Diller ve şablonlar için merkezi tanımlar
"""

# Dil yapısı: key (İngilizce kod), name_tr, name_en
LANGUAGES = {
    "tr": {
        "name_tr": "Türkçe",
        "name_en": "Turkish",
    },
    "en": {
        "name_tr": "İngilizce",
        "name_en": "English",
    },
    "de": {
        "name_tr": "Almanca",
        "name_en": "German",
    },
    "fr": {
        "name_tr": "Fransızca",
        "name_en": "French",
    },
    "es": {
        "name_tr": "İspanyolca",
        "name_en": "Spanish",
    },
    "it": {
        "name_tr": "İtalyanca",
        "name_en": "Italian",
    },
    "pt": {
        "name_tr": "Portekizce",
        "name_en": "Portuguese",
    },
    "ru": {
        "name_tr": "Rusça",
        "name_en": "Russian",
    },
    "zh": {
        "name_tr": "Çince",
        "name_en": "Chinese",
    },
    "ja": {
        "name_tr": "Japonca",
        "name_en": "Japanese",
    },
    "ko": {
        "name_tr": "Korece",
        "name_en": "Korean",
    },
    "ar": {
        "name_tr": "Arapça",
        "name_en": "Arabic",
    },
}


# Preset yapısı: key (İngilizce), name_tr, description, exaggeration, cfg_weight
PRESETS = {
    # Temel
    "default": {
        "name_tr": "Varsayılan",
        "description": "Dengeli, nötr ses",
        "exaggeration": 0.5,
        "cfg_weight": 0.5,
    },
    "casual": {
        "name_tr": "Günlük Konuşma",
        "description": "Samimi, doğal konuşma tonu",
        "exaggeration": 0.6,
        "cfg_weight": 0.6,
    },
    
    # Profesyonel
    "news_anchor": {
        "name_tr": "Haber Spikeri",
        "description": "Resmi, net ve anlaşılır",
        "exaggeration": 0.3,
        "cfg_weight": 0.8,
    },
    "commercial": {
        "name_tr": "Reklam Seslendirme",
        "description": "Enerjik, vurgulu ve dikkat çekici",
        "exaggeration": 0.9,
        "cfg_weight": 0.7,
    },
    "formal": {
        "name_tr": "Resmi Duyuru",
        "description": "Ciddi, profesyonel ton",
        "exaggeration": 0.2,
        "cfg_weight": 0.9,
    },
    "podcast": {
        "name_tr": "Podcast",
        "description": "Samimi ve rahat anlatım",
        "exaggeration": 0.4,
        "cfg_weight": 0.6,
    },
    
    # Hikaye & Sanat
    "storyteller": {
        "name_tr": "Hikaye Anlatıcı",
        "description": "Canlı ve etkileyici hikaye anlatımı",
        "exaggeration": 0.8,
        "cfg_weight": 0.5,
    },
    "kids_story": {
        "name_tr": "Çocuk Hikayesi",
        "description": "Eğlenceli ve enerjik çocuk hikayesi",
        "exaggeration": 1.0,
        "cfg_weight": 0.5,
    },
    "poetry": {
        "name_tr": "Şiir Okuma",
        "description": "Duygusal ve akıcı şiir yorumu",
        "exaggeration": 0.7,
        "cfg_weight": 0.4,
    },
    "dramatic": {
        "name_tr": "Dramatik",
        "description": "Yoğun duygusal ifade",
        "exaggeration": 1.2,
        "cfg_weight": 0.4,
    },
    
    # Duygusal
    "excited": {
        "name_tr": "Heyecanlı",
        "description": "Coşkulu ve heyecan dolu",
        "exaggeration": 1.3,
        "cfg_weight": 0.5,
    },
    "scared": {
        "name_tr": "Korkulu",
        "description": "Tedirgin ve korku dolu",
        "exaggeration": 1.1,
        "cfg_weight": 0.3,
    },
    "sad": {
        "name_tr": "Üzgün",
        "description": "Melankolik ve hüzünlü",
        "exaggeration": 0.4,
        "cfg_weight": 0.3,
    },
    "romantic": {
        "name_tr": "Romantik",
        "description": "Yumuşak ve duygusal",
        "exaggeration": 0.6,
        "cfg_weight": 0.4,
    },
    "angry": {
        "name_tr": "Sinirli",
        "description": "Öfkeli ve sert",
        "exaggeration": 1.4,
        "cfg_weight": 0.6,
    },
    
    # Özel
    "robot": {
        "name_tr": "Robot",
        "description": "Mekanik, monoton ses",
        "exaggeration": 0.1,
        "cfg_weight": 0.9,
    },
    "asmr": {
        "name_tr": "ASMR / Fısıltılı",
        "description": "Yumuşak, sakin fısıltı",
        "exaggeration": 0.2,
        "cfg_weight": 0.3,
    },
    "energetic": {
        "name_tr": "Enerji Dolu",
        "description": "Maksimum enerji ve coşku",
        "exaggeration": 1.5,
        "cfg_weight": 0.5,
    },
}


# Preset grupları (UI için)
PRESET_GROUPS = {
    "basic": {
        "name_tr": "Temel",
        "presets": ["default", "casual"],
    },
    "professional": {
        "name_tr": "Profesyonel",
        "presets": ["news_anchor", "commercial", "formal", "podcast"],
    },
    "story": {
        "name_tr": "Hikaye & Sanat",
        "presets": ["storyteller", "kids_story", "poetry", "dramatic"],
    },
    "emotional": {
        "name_tr": "Duygusal",
        "presets": ["excited", "scared", "sad", "romantic", "angry"],
    },
    "special": {
        "name_tr": "Özel",
        "presets": ["robot", "asmr", "energetic"],
    },
}


# Helper fonksiyonlar
def get_language_name_tr(code: str) -> str:
    """Dil kodundan Türkçe isim döndür"""
    return LANGUAGES.get(code, {}).get("name_tr", code)


def get_preset_name_tr(key: str) -> str:
    """Preset key'inden Türkçe isim döndür"""
    return PRESETS.get(key, {}).get("name_tr", key)


def get_language_choices_tr() -> list:
    """UI için Türkçe dil seçenekleri: [(Türkçe isim, kod), ...]"""
    return [(v["name_tr"], k) for k, v in LANGUAGES.items()]


def get_preset_choices_tr() -> list:
    """UI için Türkçe preset seçenekleri: [(Türkçe isim, key), ...]"""
    return [(v["name_tr"], k) for k, v in PRESETS.items()]


# API için basit listeler
LANGUAGE_CODES = list(LANGUAGES.keys())
PRESET_KEYS = list(PRESETS.keys())
