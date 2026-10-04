import re
from pathlib import Path
import pypdf


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extrae y sanea todo el texto plano de un documento PDF utilizando pypdf.

    Args:
        pdf_path: Ruta al archivo PDF en el sistema.

    Returns:
        Texto extraído unificado y limpio.

    Raises:
        FileNotFoundError: Si el archivo PDF no existe.
        ValueError: Si el archivo no es un documento PDF válido.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo PDF en: {path}")

    try:
        reader = pypdf.PdfReader(str(path))
    except Exception as exc:
        raise ValueError(f"Error al abrir el documento PDF {path}: {exc}") from exc

    extracted_pages: list[str] = []
    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        # Limpieza de caracteres nulos y normalización de espacios continuos
        page_text = page_text.replace("\x00", "")
        # Eliminar pies de página repetitivos de LinkedIn (ej. "Page 1 of 4")
        page_text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", page_text, flags=re.IGNORECASE)
        extracted_pages.append(page_text.strip())

    full_text = "\n\n".join(p for p in extracted_pages if p)
    # Reducir secuencias excesivas de saltos de línea (más de 3 seguidos)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    return full_text.strip()
