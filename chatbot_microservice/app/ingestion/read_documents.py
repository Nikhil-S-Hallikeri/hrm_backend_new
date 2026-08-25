import re
import subprocess
import sys
from pathlib import Path

from docx import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".docs", ".txt", ".md", ".rtf"}


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_legacy_doc(path: Path) -> str:
    """Read legacy .doc, .docs, or .rtf files using macOS textutil or a string extraction fallback."""
    if sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(path)],
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8"
            )
            return res.stdout
        except Exception:
            try:
                res = subprocess.run(
                    ["textutil", "-convert", "txt", "-stdout", str(path)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return res.stdout
            except Exception as exc:
                print(f"textutil failed to read {path}: {exc}")

    # Fallback: Extract ASCII and UTF-16LE printable strings from binary
    try:
        content = path.read_bytes()
        ascii_strings = re.findall(rb"[\x20-\x7e\x0a\x0d]{4,}", content)
        utf16_strings = re.findall(rb"(?:[\x20-\x7e\x0a\x0d]\x00){4,}", content)
        
        extracted = []
        for s in ascii_strings:
            try:
                extracted.append(s.decode("ascii"))
            except Exception:
                pass
        for s in utf16_strings:
            try:
                extracted.append(s.decode("utf-16le"))
            except Exception:
                pass
        return "\n".join(extracted)
    except Exception as exc:
        print(f"Fallback binary reader failed for {path}: {exc}")
        return ""


def read_documents(directory: Path) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    if not directory.exists():
        return documents

    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            ext = path.suffix.lower()
            if ext == ".pdf":
                text = read_pdf(path)
            elif ext == ".docx":
                text = read_docx(path)
            elif ext in {".doc", ".docs", ".rtf"}:
                text = read_legacy_doc(path)
            else:
                text = read_text_file(path)
        except Exception as exc:
            print(f"Skipped {path}: {exc}")
            continue

        text = text.strip()
        if text:
            documents.append({"path": str(path), "text": text})

    return documents
