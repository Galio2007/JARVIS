import re
from pathlib import Path


def is_empty_note(p: Path):
    """Empty, or only frontmatter / headings."""
    try:
        t = p.read_text("utf-8")
    except Exception:
        return False
    t = re.sub(r"\A---\n.*?\n---\n?", "", t, flags=re.S)
    t = re.sub(r"^\s*#+.*$", "", t, flags=re.M)
    return not t.strip()


def read_domain(text):
    """Your old organiser's rule: '[Folder Destination: X]' first, then YAML 'domain: X'."""
    m = re.search(r"\[Folder Destination:\s*(.*?)\]", text, re.I)
    if m:
        d = m.group(1)
    else:
        m = re.search(r"^domain:\s*[\"']?(.*?)[\"']?\s*$", text, re.M | re.I)
        d = m.group(1) if m else None
    if d:
        d = re.sub(r'[\\/:*?"<>|]', "", d).strip()
    return d or None


def in_dictionary(p: Path, notes: Path, dname: str):
    try:
        rel = p.relative_to(notes)
    except ValueError:
        return False
    return any(part.casefold() == dname.casefold() for part in rel.parts[:-1])


def domains(droot: Path):
    if not droot.is_dir():
        return []
    return sorted(d.name for d in droot.iterdir() if d.is_dir() and not d.name.startswith("."))


def find_in_dictionary(term, droot: Path):
    if droot.is_dir():
        for f in droot.rglob("*.md"):
            if f.stem.lower() == term.lower() and not is_empty_note(f):
                return f
    return None


def find_lessons(term, root: Path, dname, first_only=False, only=None, include_dictionary=False):
    """Notes under root containing [[term]], [[term|alias]], [[term#h]], [[folder/term]].
    The dictionary folder and hidden folders are not searched."""
    pat = re.compile(r"\[\[\s*(?:[^\]|#]*/)?" + re.escape(term) +
                     r"\s*(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]", re.I)
    hits = []
    for f in sorted(root.rglob("*.md")):
        parts = f.relative_to(root).parts
        if any(x.startswith(".") for x in parts):
            continue
        in_dict = any(x.casefold() == dname.casefold() for x in parts)
        if in_dict and not include_dictionary:
            continue
        if only and not in_dict and (len(parts) < 2 or parts[0].casefold() not in only):
            continue
        txt = f.read_text("utf-8", errors="ignore")
        m = pat.search(txt)
        if m:
            hits.append((f, txt, m.start()))
            if first_only:
                break
    return hits


def has_backlink(term, notes, dname, only=None):
    return bool(find_lessons(term, notes, dname, first_only=True, only=only, include_dictionary=True))


def heading_before(text, pos):
    heads = re.findall(r"^#{1,6}\s+(.+)$", text[:pos], re.M)
    return heads[-1].strip() if heads else ""


def cut_at(text, marker):
    if not marker:
        return text
    m = re.search(re.escape(marker), text, re.I)
    return text[: m.start()].rstrip() if m else text
