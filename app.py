"""
AutomationX TTS
"""

import gradio as gr
import uvicorn
import os
from dotenv import load_dotenv

from core import (
    get_state,
    logger,
)
from api import api_app
from ui import create_ui

# Environment yükle
load_dotenv()

state = get_state()

gradio_ui = create_ui()

app = gr.mount_gradio_app(api_app, gradio_ui, path="/")

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 7777))
    logger.info(f"AutomationX TTS başlatılıyor {host}:{port}...")
    logger.info(f"UI: http://{host}:{port}")
    logger.info(f"API Docs: http://{host}:{port}/docs")
    logger.info(f"API Endpoint: http://{host}:{port}/generate")
    
    # Development modunda reload
    uvicorn.run("app:app", host=host, port=port, reload=True)
