"""
AutomationX TTS - Utilities
Shared utility functions for text and audio processing.
"""

import re
import torch

def split_into_sentences(text: str, max_chars: int = 200) -> list:
    """
    Metni cümlelere böl. Çok uzun cümleler varsa noktalama yerlerinden kes.
    """
    # Cümle sonu işaretleri
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_endings.split(text.strip())
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Cümle çok uzunsa, virgül/noktalı virgül yerinden böl
        if len(sentence) > max_chars:
            sub_parts = re.split(r'(?<=[,;:])\s+', sentence)
            for part in sub_parts:
                if len(current_chunk) + len(part) + 1 <= max_chars:
                    current_chunk = f"{current_chunk} {part}".strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = part
        else:
            if len(current_chunk) + len(sentence) + 1 <= max_chars:
                current_chunk = f"{current_chunk} {sentence}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks if chunks else [text]


def merge_audio_with_crossfade(segments: list, sample_rate: int, 
                                silence_ms: int = 150, 
                                fade_ms: int = 30) -> torch.Tensor:
    """
    Audio segmentlerini crossfade ve sessizlik ile birleştir.
    
    Args:
        segments: Audio tensor listesi (her biri [1, samples] boyutunda)
        sample_rate: Örnekleme hızı
        silence_ms: Segmentler arası sessizlik (ms)
        fade_ms: Fade in/out süresi (ms)
    """
    if len(segments) == 1:
        return segments[0]
    
    silence_samples = int(sample_rate * silence_ms / 1000)
    fade_samples = int(sample_rate * fade_ms / 1000)
    
    # Fade curves
    fade_out = torch.linspace(1.0, 0.0, fade_samples)
    fade_in = torch.linspace(0.0, 1.0, fade_samples)
    
    processed = []
    for i, seg in enumerate(segments):
        seg = seg.clone()
        
        # Fade out (son kısım) - ilk segment hariç hepsine uygula
        if seg.shape[1] > fade_samples:
            seg[0, -fade_samples:] *= fade_out
        
        # Fade in (baş kısım) - son segment hariç hepsine uygula  
        if i > 0 and seg.shape[1] > fade_samples:
            seg[0, :fade_samples] *= fade_in
        
        processed.append(seg)
        
        # Segmentler arası sessizlik ekle (son segment hariç)
        if i < len(segments) - 1:
            processed.append(torch.zeros(1, silence_samples))
    
    return torch.cat(processed, dim=1)
