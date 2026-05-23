"""PDF text extraction. Uses pdfplumber; falls back to Claude vision for scanned docs."""
from pathlib import Path
from typing import Optional
import base64
import pdfplumber
import anthropic
from investimentos.config import get_settings

def extract_text_from_pdf(path: Path) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
    return "\n".join(text_parts)

def extract_with_claude_vision(path: Path, prompt: str) -> str:
    """Use Claude vision for scanned PDF documents."""
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    with open(path, "rb") as f:
        pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")
    message = client.messages.create(
        model=settings.llm_model_default,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return message.content[0].text

def extract_pdf(path: Path, prompt: Optional[str] = None) -> str:
    """Primary extractor: tries pdfplumber first, falls back to Claude vision."""
    text = extract_text_from_pdf(path)
    if text.strip():
        return text
    fallback_prompt = prompt or (
        "Extraia o conteúdo estruturado deste documento. "
        "Identifique: tipo do documento, datas, valores, tickers de ativos e quantidades."
    )
    return extract_with_claude_vision(path, fallback_prompt)
