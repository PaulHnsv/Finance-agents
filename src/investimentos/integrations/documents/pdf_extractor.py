"""PDF text extraction. Uses pdfplumber; falls back to GPT-4o vision (via GitHub Models) for scanned docs."""
import base64
import io
from pathlib import Path
from typing import Optional

import pdfplumber

from investimentos.config import get_settings
from investimentos.llm.client import get_llm_client


def extract_text_from_pdf(path: Path) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
    return "\n".join(text_parts)


def _render_pages_as_data_uris(path: Path, max_pages: int = 5) -> list[str]:
    data_uris: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:max_pages]:
            img = page.to_image(resolution=150)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
            data_uris.append(f"data:image/png;base64,{b64}")
    return data_uris


def extract_with_vision(path: Path, prompt: str) -> str:
    """Use GPT-4o vision (via GitHub Models) for scanned PDF documents."""
    settings = get_settings()
    client = get_llm_client()
    images = _render_pages_as_data_uris(path)
    content: list[dict] = [{"type": "text", "text": prompt}]
    for uri in images:
        content.append({"type": "image_url", "image_url": {"url": uri}})
    response = client.chat.completions.create(
        model=settings.llm_model_default,
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )
    return (response.choices[0].message.content or "").strip()


def extract_pdf(path: Path, prompt: Optional[str] = None) -> str:
    """Primary extractor: tries pdfplumber first, falls back to vision for scanned PDFs."""
    text = extract_text_from_pdf(path)
    if text.strip():
        return text
    fallback_prompt = prompt or (
        "Extraia o conteúdo estruturado deste documento. "
        "Identifique: tipo do documento, datas, valores, tickers de ativos e quantidades."
    )
    return extract_with_vision(path, fallback_prompt)
