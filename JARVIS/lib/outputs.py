import re
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz  # older PyMuPDF
from . import vault

START = re.compile(r"=== LESSON (\d+) START ===")


def convert_pdf(pdf: Path, workspace: Path) -> str:
    """BMO: PDF -> raw text (kept in work/). Raises if the PDF is scanned."""
    workspace.mkdir(exist_ok=True)
    doc = fitz.open(str(pdf))
    pages = [p.get_text() for p in doc]
    if sum(len(p.strip()) for p in pages) < 40 * max(len(pages), 1):
        raise ValueError("almost no text found; the PDF is probably scanned (needs OCR)")
    text = "\n".join(f"[p{i+1}]\n{p}" for i, p in enumerate(pages))
    (workspace / (pdf.stem + ".txt")).write_text(text, "utf-8")
    return text


def chunk(text, max_words=5000):
    pages = re.split(r"(?=\[p\d+\]\n)", text)
    chunks, cur, n = [], [], 0
    for p in pages:
        w = len(p.split())
        if cur and n + w > max_words:
            chunks.append("".join(cur)); cur, n = [], 0
        cur.append(p); n += w
    if cur:
        chunks.append("".join(cur))
    return chunks


def strip_fence(t):
    t = t.strip()
    m = re.fullmatch(r"```[\w-]*\n(.*)\n```", t, re.S)
    return m.group(1) if m else t


def save_note(path: Path, reply: str):
    """Fill an empty/title-only note. Never overwrites real content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text("utf-8") if path.exists() else ""
    if old.strip() and not vault.is_empty_note(path):
        raise FileExistsError(f"{path.name} already has content; not touching it")
    new = (old.rstrip() + "\n\n" if old.strip() else "") + strip_fence(reply) + "\n"
    path.write_text(new, "utf-8")


def split_lessons(text, out_dir: Path):
    """Rattleballs: cut at '=== LESSON X START ===' and write one .md per lesson."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pat = re.compile(r"=== LESSON (\d+) START ===\s*(.*?)(?=(?:=== LESSON \d+ START ===)|\Z)", re.S)
    files = []
    for num, body in pat.findall(text):
        body = re.sub(r"=== LESSON \d+ END ===", "", body).strip()
        t = re.search(r"^#+\s*(.+)$", body, re.M)
        slug = re.sub(r"[^\w\-]+", "_", t.group(1)).strip("_")[:50] if t else "lesson"
        f = out_dir / f"lesson_{int(num):02d}_{slug}.md"
        i = 2
        while f.exists():
            f = out_dir / f"lesson_{int(num):02d}_{slug}_{i}.md"; i += 1
        f.write_text(body + "\n", "utf-8")
        files.append(f)
    return files
