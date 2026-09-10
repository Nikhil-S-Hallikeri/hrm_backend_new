from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from openai import OpenAI

from app.config import get_settings
from app.ingestion.crawl_website import crawl_site
from app.ingestion.read_documents import read_documents

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
settings = get_settings()
DOCS_DIR = Path(getattr(settings, "docs_dir", str(DATA_DIR / "docs"))).resolve()
BUILD_DIR = DATA_DIR / "build"
KNOWLEDGE_FILE = BUILD_DIR / "academy_knowledge.txt"


def _website_url_variants(url: str) -> list[str]:
    parsed = urlparse(url)
    if not parsed.netloc:
        parsed = urlparse(f"https://{url}")
    host = parsed.netloc
    bare_host = host[4:] if host.startswith("www.") else host
    hosts = [host, bare_host, f"www.{bare_host}"]
    schemes = [parsed.scheme or "https", "https", "http"]
    variants: list[str] = []
    for scheme in schemes:
        for candidate_host in hosts:
            candidate = urlunparse((scheme, candidate_host, parsed.path or "", "", "", "")).rstrip("/")
            if candidate not in variants:
                variants.append(candidate)
    return variants


def build_local_knowledge_file() -> Path:
    settings = get_settings()
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    chunks: list[str] = []

    docs = read_documents(DOCS_DIR)
    print(f"Collected {len(docs)} local documents.")
    for doc in docs:
        chunks.append(f"Source File: {Path(doc['path']).name}\n\n{doc['text']}")

    pages: list[dict[str, str]] = []
    if settings.crawl_website and settings.website_url:
        for website_url in _website_url_variants(settings.website_url):
            print(f"Crawling {website_url} ...")
            pages = crawl_site(website_url, max_pages=settings.crawl_max_pages, timeout=settings.crawl_timeout)
            if pages:
                break
    else:
        print("Website crawl skipped. Set CRAWL_WEBSITE=true to enable it.")

    print(f"Collected {len(pages)} website pages.")
    for page in pages:
        chunks.append(
            f"PAGE TITLE:\n{page['title']}\n\nSOURCE URL:\n{page['url']}\n\nPAGE CONTENT:\n{page['text']}"
        )

    if not chunks:
        chunks.append(
            f"Source: Starter profile\n\n{settings.academy_name}\n\nNo website pages or documents were collected. Add PDFs, DOCX, TXT, or MD files to data/docs and rerun ingestion."
        )
        print("No website pages or documents were collected. A starter knowledge file will be created instead.")

    KNOWLEDGE_FILE.write_text("\n\n---\n\n".join(chunks), encoding="utf-8")
    return KNOWLEDGE_FILE


def upload_to_openai(file_path: Path) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing in .env")
    client = OpenAI(api_key=settings.openai_api_key)
    vector_store = client.vector_stores.create(
        name=f"{settings.academy_name} Knowledge Base",
        description=f"Website and document knowledge for {settings.academy_name}.",
    )
    with file_path.open("rb") as file_stream:
        uploaded_file = client.files.create(file=file_stream, purpose="assistants")
    client.vector_stores.files.create_and_poll(
        vector_store_id=vector_store.id,
        file_id=uploaded_file.id,
        attributes={"source": "website_and_documents", "academy": settings.academy_name},
    )
    return vector_store.id


def main():
    load_dotenv()
    file_path = build_local_knowledge_file()
    print(f"Knowledge file written to: {file_path}")
    settings = get_settings()
    if settings.ai_provider != "openai":
        print(f"\n{settings.ai_provider} mode is enabled.")
        print("The local knowledge file is ready and will be used as chat context.")
        print("No OPENAI_VECTOR_STORE_ID is needed unless you switch AI_PROVIDER=openai.")
        return
    vector_store_id = upload_to_openai(file_path)
    print("\nKnowledge base ready.")
    print(f"OPENAI_VECTOR_STORE_ID={vector_store_id}")


if __name__ == "__main__":
    main()

import csv
import io
import tempfile

def parse_csv_faq(file_bytes: bytes) -> str:
    try:
        text = file_bytes.decode('utf-8', errors='ignore')
    except Exception:
        text = file_bytes.decode('latin-1', errors='ignore')
        
    reader = csv.reader(io.StringIO(text))
    rows = []
    for row in reader:
        if not row:
            continue
        if len(row) >= 2:
            rows.append(f"Q: {row[0].strip()}\nA: {row[1].strip()}")
        elif len(row) == 1:
            rows.append(f"Q/Topic: {row[0].strip()}")
    return "\n\n".join(rows)

def append_knowledge_source(
    file_name: str | None = None,
    file_bytes: bytes | None = None,
    url: str | None = None,
    faq_q: str | None = None,
    faq_a: str | None = None
) -> Path:
    from app.ingestion.read_documents import read_pdf, read_docx, read_text_file, read_legacy_doc
    
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    text_to_append = ""
    
    if file_name and file_bytes:
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = DOCS_DIR / file_name
        dest_path.write_bytes(file_bytes)
        
        suffix = dest_path.suffix.lower()
        if suffix == ".csv":
            extracted = parse_csv_faq(file_bytes)
            text_to_append = f"Source FAQ File: {file_name}\n\n{extracted}"
        else:
            if suffix == ".pdf":
                extracted = read_pdf(dest_path)
            elif suffix == ".docx":
                extracted = read_docx(dest_path)
            elif suffix in {".doc", ".docs", ".rtf"}:
                extracted = read_legacy_doc(dest_path)
            else:
                extracted = read_text_file(dest_path)
            text_to_append = f"Source Document File: {file_name}\n\n{extracted}"
                    
    elif url:
        print(f"Crawling website: {url} ...")
        pages = crawl_site(url, max_pages=15)
        chunks = []
        for page in pages:
            chunks.append(
                f"PAGE TITLE:\n{page['title']}\n\nSOURCE URL:\n{page['url']}\n\nPAGE CONTENT:\n{page['text']}"
            )
        if chunks:
            text_to_append = "\n\n---\n\n".join(chunks)
        else:
            text_to_append = f"Source Link: {url}\n\nNo page content crawled."
            
    elif faq_q:
        answer = faq_a or "No answer provided."
        text_to_append = f"FAQ Q&A:\nQ: {faq_q}\nA: {answer}"
        
    if text_to_append:
        mode = "a" if KNOWLEDGE_FILE.exists() else "w"
        with KNOWLEDGE_FILE.open(mode, encoding="utf-8") as f:
            if mode == "a":
                f.write("\n\n---\n\n")
            f.write(text_to_append.strip())
            
    return KNOWLEDGE_FILE