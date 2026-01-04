"""
AutomationX TTS - Text Normalizer
Sayıları, tarihleri, saatleri ve özel formatları Türkçe metne çevirir.
"""

import re
from typing import Optional

# ===================================================================
# TÜRKÇE SAYI İSİMLERİ
# ===================================================================

ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
SCALES = [
    (1_000_000_000_000, "trilyon"),
    (1_000_000_000, "milyar"),
    (1_000_000, "milyon"),
    (1_000, "bin"),
    (100, "yüz"),
]

ORDINALS = {
    1: "birinci", 2: "ikinci", 3: "üçüncü", 4: "dördüncü", 5: "beşinci",
    6: "altıncı", 7: "yedinci", 8: "sekizinci", 9: "dokuzuncu", 10: "onuncu",
}


def number_to_turkish(n: int) -> str:
    """Sayıyı Türkçe metne çevir."""
    if n == 0:
        return "sıfır"
    
    if n < 0:
        return "eksi " + number_to_turkish(-n)
    
    result = []
    
    for scale, name in SCALES:
        if n >= scale:
            count = n // scale
            n %= scale
            
            if scale == 1000 and count == 1:
                result.append(name)  # "bir bin" değil "bin"
            elif scale == 100 and count == 1:
                result.append(name)  # "bir yüz" değil "yüz"
            else:
                if count >= 100:
                    result.append(number_to_turkish(count))
                elif count >= 10:
                    result.append(TENS[count // 10])
                    if count % 10:
                        result.append(ONES[count % 10])
                else:
                    result.append(ONES[count])
                result.append(name)
    
    if n >= 10:
        result.append(TENS[n // 10])
        n %= 10
    
    if n > 0:
        result.append(ONES[n])
    
    return " ".join(filter(None, result))


def decimal_to_turkish(num_str: str) -> str:
    """Ondalık sayıyı Türkçe'ye çevir."""
    if "." in num_str or "," in num_str:
        num_str = num_str.replace(",", ".")
        parts = num_str.split(".")
        integer_part = number_to_turkish(int(parts[0]))
        decimal_part = " ".join(ONES[int(d)] if d != "0" else "sıfır" for d in parts[1])
        return f"{integer_part} virgül {decimal_part}"
    return number_to_turkish(int(num_str))


# ===================================================================
# NORMALIZER PATTERNS
# ===================================================================

def normalize_percentages(text: str) -> str:
    """Yüzdeleri çevir: %50 -> yüzde elli"""
    def replace(m):
        num = m.group(1)
        return f"yüzde {decimal_to_turkish(num)}"
    return re.sub(r"%(\d+(?:[.,]\d+)?)", replace, text)


def normalize_currency(text: str) -> str:
    """Para birimlerini çevir: 100₺ -> yüz lira, $50 -> elli dolar"""
    patterns = [
        (r"(\d+(?:[.,]\d+)?)\s*₺", lambda m: f"{decimal_to_turkish(m.group(1))} lira"),
        (r"(\d+(?:[.,]\d+)?)\s*TL", lambda m: f"{decimal_to_turkish(m.group(1))} lira"),
        (r"\$(\d+(?:[.,]\d+)?)", lambda m: f"{decimal_to_turkish(m.group(1))} dolar"),
        (r"€(\d+(?:[.,]\d+)?)", lambda m: f"{decimal_to_turkish(m.group(1))} euro"),
        (r"£(\d+(?:[.,]\d+)?)", lambda m: f"{decimal_to_turkish(m.group(1))} sterlin"),
    ]
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def normalize_time(text: str) -> str:
    """Saatleri çevir: 15:30 -> on beş otuz"""
    def replace(m):
        hour = int(m.group(1))
        minute = int(m.group(2))
        hour_str = number_to_turkish(hour)
        if minute == 0:
            return hour_str
        minute_str = number_to_turkish(minute)
        return f"{hour_str} {minute_str}"
    return re.sub(r"(\d{1,2}):(\d{2})", replace, text)


def normalize_dates(text: str) -> str:
    """Tarihleri çevir: 31.12.2024 -> otuz bir aralık iki bin yirmi dört"""
    months = {
        1: "ocak", 2: "şubat", 3: "mart", 4: "nisan",
        5: "mayıs", 6: "haziran", 7: "temmuz", 8: "ağustos",
        9: "eylül", 10: "ekim", 11: "kasım", 12: "aralık"
    }
    
    def replace(m):
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3))
        
        day_str = number_to_turkish(day)
        month_str = months.get(month, str(month))
        year_str = number_to_turkish(year)
        
        return f"{day_str} {month_str} {year_str}"
    
    # DD.MM.YYYY veya DD/MM/YYYY
    text = re.sub(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", replace, text)
    return text


def normalize_years(text: str) -> str:
    """Yılları çevir: 2026 -> iki bin yirmi altı (bağlamda)"""
    def replace(m):
        year = int(m.group(0))
        if 1900 <= year <= 2100:
            return number_to_turkish(year)
        return m.group(0)
    
    # Tek başına 4 haneli yıllar (kelime sınırında)
    return re.sub(r"\b(19|20)\d{2}\b", replace, text)


def normalize_ordinals(text: str) -> str:
    """Sıra sayılarını çevir: 1. -> birinci, 2. -> ikinci"""
    def replace(m):
        num = int(m.group(1))
        if num in ORDINALS:
            return ORDINALS[num]
        return f"{number_to_turkish(num)}inci"  # Basitleştirilmiş
    
    return re.sub(r"(\d+)\.", replace, text)


def normalize_standalone_numbers(text: str) -> str:
    """Kalan sayıları çevir"""
    def replace(m):
        num_str = m.group(0)
        try:
            if "." in num_str or "," in num_str:
                return decimal_to_turkish(num_str)
            return number_to_turkish(int(num_str))
        except:
            return num_str
    
    # Ondalık veya tam sayı
    return re.sub(r"\b\d+(?:[.,]\d+)?\b", replace, text)


# ===================================================================
# MAIN NORMALIZER
# ===================================================================

def normalize_text(text: str) -> str:
    """
    Metni TTS için normalize et.
    Sıra önemli - önce özel formatlar, sonra genel sayılar.
    """
    # 1. Yüzdeler
    text = normalize_percentages(text)
    
    # 2. Para birimleri
    text = normalize_currency(text)
    
    # 3. Saatler
    text = normalize_time(text)
    
    # 4. Tarihler
    text = normalize_dates(text)
    
    # 5. Yıllar (tarihlerden sonra, çünkü tarihler içinde yıl var)
    text = normalize_years(text)
    
    # 6. Sıra sayıları (1., 2., vb.)
    text = normalize_ordinals(text)
    
    # 7. Kalan sayılar
    text = normalize_standalone_numbers(text)
    
    # Fazla boşlukları temizle
    text = re.sub(r"\s+", " ", text).strip()
    
    return text
