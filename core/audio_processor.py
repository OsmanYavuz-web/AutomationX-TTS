"""
AutomationX TTS - Audio Processing Filters
Ses kalitesini artıran filtreler
"""

import torch
import torchaudio.functional as F


def apply_lowpass(wav: torch.Tensor, sr: int, cutoff: int = 10000) -> torch.Tensor:
    """Lowpass filter - yüksek frekanslı tıslama/cızırtıyı keser"""
    return F.lowpass_biquad(wav, sr, cutoff_freq=cutoff)


def apply_highpass(wav: torch.Tensor, sr: int, cutoff: int = 80) -> torch.Tensor:
    """Highpass filter - düşük frekanslı uğultuyu keser"""
    return F.highpass_biquad(wav, sr, cutoff_freq=cutoff)


def apply_noise_gate(wav: torch.Tensor, threshold_db: float = -45) -> torch.Tensor:
    """
    Noise Gate - sessiz kısımlardaki parazitleri sıfırlar.
    """
    threshold_linear = 10 ** (threshold_db / 20)
    abs_wav = torch.abs(wav)
    gate_mask = (abs_wav > threshold_linear).float()
    
    # Yumuşak geçiş için smoothing
    kernel_size = 101
    if wav.shape[1] > kernel_size:
        padding = kernel_size // 2
        gate_mask_smooth = torch.nn.functional.avg_pool1d(
            gate_mask.unsqueeze(0), kernel_size, stride=1, padding=padding
        ).squeeze(0)
        gate_mask_smooth = torch.clamp(gate_mask_smooth, 0, 1)
    else:
        gate_mask_smooth = gate_mask
    
    return wav * gate_mask_smooth


def apply_normalize(wav: torch.Tensor, target_db: float = -3.0) -> torch.Tensor:
    """Normalize - optimal ses seviyesine çeker."""
    peak = torch.max(torch.abs(wav))
    if peak > 0:
        target_linear = 10 ** (target_db / 20)
        gain = target_linear / peak
        return wav * gain
    return wav


class AudioProcessor:
    """Ses işleme pipeline'ı."""
    
    def __init__(self, config: dict):
        self.highpass_freq = config.get("highpass_freq", 80)
        self.lowpass_freq = config.get("lowpass_freq", 10000)
        self.noise_gate_threshold = config.get("noise_gate_threshold", -45)
        self.normalize_audio = config.get("normalize_audio", True)
    
    def process(self, wav: torch.Tensor, sr: int) -> torch.Tensor:
        """Filtreleri sırayla uygula"""
        
        # 1. Highpass - düşük frekanslı uğultuyu kes
        wav = apply_highpass(wav, sr, self.highpass_freq)
        
        # 2. Lowpass - yüksek frekanslı tıslamayı kes
        wav = apply_lowpass(wav, sr, self.lowpass_freq)
        
        # 3. Noise Gate - sessiz kısımlardaki paraziti temizle
        if self.noise_gate_threshold > -100:
            wav = apply_noise_gate(wav, self.noise_gate_threshold)
        
        # 4. Normalize - ses seviyesini optimize et
        if self.normalize_audio:
            wav = apply_normalize(wav)
        
        return wav
