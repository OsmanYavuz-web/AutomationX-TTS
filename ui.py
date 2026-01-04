"""
AutomationX TTS - User Interface (Gradio)
"""

import gradio as gr
import torch
import torchaudio as ta
import os
import random
from datetime import datetime

from core import (
    get_state,
    error_boundary,
    strict_operation,
    logger,
    ValidationError,
    normalize_text,
    AudioProcessor,
    LANGUAGES,
    PRESETS,
    PRESET_GROUPS,
    get_language_choices_tr,

    split_into_sentences,
    merge_audio_with_crossfade,
)

# state is singleton
state = get_state()

# Helper functions for UI
def get_history_choices():
    history = state.load_history(limit=20)
    choices = []
    for h in history:
        text_preview = h["text"][:30] + "..." if len(h["text"]) > 30 else h["text"]
        label = f"{h['timestamp']} - {text_preview}"
        choices.append((label, h["filename"]))
    return choices

@error_boundary(default_return=None)
def play_history_audio(filename):
    if not filename:
        return None
    filepath = os.path.join(state.outputs_dir, filename)
    if os.path.exists(filepath):
        return filepath
    return None

@strict_operation
def generate_speech(text, language, ref_audio, exaggeration, cfg_weight, seed, progress=gr.Progress()):
    if not text.strip():
        raise ValidationError("Lutfen bir metin girin!")
    
    # Seed ayarla
    actual_seed = int(seed) if seed >= 0 else random.randint(0, 999999)
    torch.manual_seed(actual_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(actual_seed)
    
    progress(0.1, desc="Model yukleniyor...")
    tts = state.tts_model
    
    lang_code = language if language in LANGUAGES else "tr"
    
    if lang_code == "tr":
        normalized_text = normalize_text(text)
        logger.info(f"Normalized: {text[:50]}... -> {normalized_text[:50]}...")
    else:
        normalized_text = text
    
    chunks = split_into_sentences(normalized_text, max_chars=200)
    total_chunks = len(chunks)
    
    logger.info(f"Processing {total_chunks} chunks...")
    
    audio_segments = []
    for i, chunk in enumerate(chunks):
        progress_val = 0.1 + (0.7 * (i / total_chunks))
        progress(progress_val, desc=f"Ses uretiliyor... ({i+1}/{total_chunks})")
        
        chunk_seed = actual_seed + i # Deterministic per chunk but different
        
        # Retry logic for stability
        wav_chunk = None
        for attempt in range(3):
            try:
                # Set seed for this attempt
                current_seed = chunk_seed + (attempt * 100)
                torch.manual_seed(current_seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed(current_seed)
                
                wav_chunk = tts.generate(
                    chunk,
                    language_id=lang_code,
                    audio_prompt_path=ref_audio if ref_audio else None,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                )
                break # Success
            except RuntimeError as e:
                logger.warning(f"Chunk generation failed (attempt {attempt+1}): {e}")
                if attempt == 2:
                     logger.error(f"Skipping chunk after 3 failures: {chunk[:20]}...")
                     # Create silent chunk of 0.5s as placeholder
                     wav_chunk = torch.zeros(1, int(tts.sr * 0.5))
        
        if wav_chunk is not None:
             audio_segments.append(wav_chunk)
    
    progress(0.85, desc="Parcalar birlestiriliyor...")
    if len(audio_segments) > 1:
        wav = merge_audio_with_crossfade(audio_segments, tts.sr)
    else:
        wav = audio_segments[0]
    
    progress(0.88, desc="Ses filtreleniyor...")
    audio_processor = AudioProcessor(state.audio_config)
    wav = audio_processor.process(wav, tts.sr)
    
    progress(0.9, desc="Kaydediliyor...")
    os.makedirs(state.outputs_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tts_{timestamp}.wav"
    filepath = os.path.join(state.outputs_dir, filename)
    ta.save(filepath, wav, tts.sr)
    
    state.save_to_history({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "text": text,
        "language": language,
        "seed": actual_seed,
        "exaggeration": exaggeration,
        "cfg_weight": cfg_weight,
        "filename": filename,
    })
    
    logger.info(f"Generated: {filename} (seed={actual_seed}, chunks={total_chunks})")
    progress(1.0, desc="Tamamlandi!")
    return filepath

def apply_preset(preset_key):
    preset = PRESETS.get(preset_key, PRESETS["default"])
    return preset["exaggeration"], preset["cfg_weight"]

def clear_all():
    return "", None, None

def refresh_history():
    return gr.update(choices=get_history_choices())

@error_boundary(default_return=(None, "Bir ses secin..."))
def on_history_select(filename):
    if not filename:
        return None, "Bir ses secin..."
    
    filepath = os.path.join(state.outputs_dir, filename)
    entry = state.get_history_entry(filename)
    
    if entry:
        info = f"""**Metin:** {entry['text']}

**Tarih:** {entry['timestamp']} | **Dil:** {entry['language']}

**Seed:** `{entry['seed']}` | **Duygu:** `{entry['exaggeration']}` | **Netlik:** `{entry['cfg_weight']}`"""
    else:
        info = "Bilgi bulunamadi."
    
    if os.path.exists(filepath):
        return filepath, info
    return None, info

@error_boundary(default_return=(0.5, 0.5, -1))
def load_history_settings(filename):
    entry = state.get_history_entry(filename)
    if entry:
        return entry["exaggeration"], entry["cfg_weight"], entry["seed"]
    return 0.5, 0.5, -1



CSS = """
:root { --accent: #8b5cf6; --bg: #0a0a0a; --surface: #141414; --surface-2: #1f1f1f; --border: #2a2a2a; --text: #fafafa; --text-dim: #888; }
.gradio-container { background: var(--bg) !important; max-width: 100% !important; padding: 24px 40px !important; }
.text-area textarea { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 12px !important; color: var(--text) !important; font-size: 1.05rem !important; lineHeight: 1.7 !important; padding: 20px !important; min-height: 150px !important; }
.text-area textarea:focus { border-color: var(--accent) !important; }
.gen-btn { background: linear-gradient(135deg, #8b5cf6, #6d28d9) !important; border: none !important; border-radius: 12px !important; color: white !important; font-size: 1.1rem !important; fontWeight: 600 !important; padding: 16px !important; }
.gen-btn:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4) !important; }
.settings-panel, .history-panel { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 16px !important; padding: 20px !important; }
.history-panel { max-height: 400px; overflow-y: auto; }
.section-title { font-size: 0.85rem; font-weight: 600; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; margin: 16px 0 10px 0; }
.seed-display { background: var(--surface-2) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; padding: 8px 12px !important; font-family: monospace !important; }
.clear-btn { background: transparent !important; border: 1px solid var(--border) !important; color: var(--text-dim) !important; }
.char-count { font-size: 1.85rem !important; color: var(--accent) !important; text-align: right !important; }
.char-count p{ font-size: 1.2rem !important; }
footer { display: none !important; }
"""

def create_ui():
    with gr.Blocks(css=CSS, theme=gr.themes.Base(), title="AutomationX TTS") as demo:
        with gr.Row():
            # LEFT
            with gr.Column(scale=2):
                char_count = gr.Markdown(value="📝 0 karakter | 0 kelime", elem_classes=["char-count"])
                text_input = gr.Textbox(placeholder="Metni buraya yazin...", lines=6, max_lines=10, show_label=False, elem_classes=["text-area"])
                with gr.Row():
                    language = gr.Dropdown(choices=get_language_choices_tr(), value="tr", show_label=False, scale=1)
                    generate_btn = gr.Button("Ses Uret", elem_classes=["gen-btn"], scale=2)
                audio_output = gr.Audio(label="Uretilen Ses", type="filepath", interactive=False)
                
                # History
                gr.HTML('<div class="section-title">SES GECMISI</div>')
                history_dropdown = gr.Dropdown(choices=get_history_choices(), value=None, label="Gecmis Sesler", interactive=True)
                history_audio = gr.Audio(label="", type="filepath", interactive=False)
                history_info = gr.Markdown(value="Bir ses secin...")
                with gr.Row():
                    load_settings_btn = gr.Button("Ayarlari Yukle", size="sm")
                    refresh_btn = gr.Button("Yenile", size="sm")
            
            # RIGHT
            with gr.Column(scale=1, elem_classes=["settings-panel"]):
                gr.HTML('<div class="section-title">ŞABLONLAR</div>')
                
                # Presets Groups
                preset_radios = []
                for group_key, group_data in PRESET_GROUPS.items():
                   with gr.Accordion(group_data["name_tr"], open=(group_key=="basic")):
                       group_presets = group_data["presets"]
                       choices = [(PRESETS[k]["name_tr"], k) for k in group_presets]
                       radio = gr.Radio(choices=choices, value="default" if group_key=="basic" else None, show_label=False)
                       preset_radios.append(radio)
                       
                gr.HTML('<div class="section-title">SES KLONU</div>')
                ref_audio = gr.Audio(type="filepath", sources=["upload"], show_label=False)
                
                gr.HTML('<div class="section-title">INCE AYARLAR</div>')
                exaggeration = gr.Slider(label="Duygu Yogunlugu", minimum=0.0, maximum=2.0, value=0.5, step=0.1)
                cfg_weight = gr.Slider(label="Metin Sadakati", minimum=0.0, maximum=1.0, value=0.5, step=0.1)
                seed = gr.Number(label="Seed (-1 = rastgele)", value=-1, precision=0)
                clear_btn = gr.Button("Temizle", elem_classes=["clear-btn"])

        # Events
        text_input.change(lambda t: f"📝 {len(t)} karakter | {len(t.split())} kelime", inputs=[text_input], outputs=[char_count])
        generate_btn.click(generate_speech, inputs=[text_input, language, ref_audio, exaggeration, cfg_weight, seed], outputs=[audio_output]).then(refresh_history, outputs=[history_dropdown])
        clear_btn.click(clear_all, outputs=[text_input, audio_output])
        
        # History events
        refresh_btn.click(refresh_history, outputs=[history_dropdown])
        history_dropdown.change(on_history_select, inputs=[history_dropdown], outputs=[history_audio, history_info])
        load_settings_btn.click(load_history_settings, inputs=[history_dropdown], outputs=[exaggeration, cfg_weight, seed])
        
        # Preset events logic (dynamic)
        all_radios = preset_radios
        for i, radio in enumerate(all_radios):
            others = [r for j, r in enumerate(all_radios) if i != j]
            
            def reset_others():
                return tuple([None] * len(others))
                
            radio.select(
                fn=apply_preset,
                inputs=[radio],
                outputs=[exaggeration, cfg_weight]
            ).then(
                fn=reset_others,
                outputs=others
            )

    return demo
