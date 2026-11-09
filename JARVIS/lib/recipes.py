import re
from dataclasses import dataclass, field
from pathlib import Path
from .config import ROOT

FOLLOW_NOTE = "New term: {term}\nUnder heading: {heading}\nSame lesson, same rules as before."
FOLLOW_PDF = ("Part {part} of {total}. Continue numbering lessons from {start_lesson}. "
              "Same rules as before; do not omit any content.\n\nSOURCE TEXT:\n{chunk}")


@dataclass
class Recipe:
    name: str
    description: str = ""
    triggers: list = field(default_factory=list)   # typed-order, new-pdf, new-empty-note
    keywords: list = field(default_factory=list)
    subjects: list = field(default_factory=list)   # empty = any subject
    inputs: list = field(default_factory=list)
    output: str = "note"                           # note | files | lessons
    output_folder: str = ""
    filename: str = "{term}.md"
    expect: str = ""                               # regex the LAST reply must contain
    reset_after: int = 30
    chunk_words: object = None                     # None = config default, 0 = whole PDF
    prompt: str = ""                               # message 1
    next: list = field(default_factory=list)       # messages 2.. (same chat, in order)
    followup: str = ""                             # used when continuing a saved chat


def _list(v):
    return [x.strip() for x in v.replace("|", ",").split(",") if x.strip()]


def parse(text):
    text = text.replace("\r\n", "\n").lstrip("\ufeff").strip()
    head, sep, body = text.partition("\n---\n")
    if not sep:
        raise ValueError("no line containing only '---' between header and prompt")
    meta = {}
    for line in head.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    if not meta.get("name"):
        raise ValueError("missing 'name:'")
    main, _, follow = body.partition("\n--- followup ---\n")
    msgs = [m.strip() for m in re.split(r"\n--- next ---\n", main)]
    cw = meta.get("chunk_words")
    return Recipe(
        name=meta["name"], description=meta.get("description", ""),
        triggers=_list(meta.get("triggers", "typed-order")),
        keywords=[k.lower() for k in _list(meta.get("keywords", ""))],
        subjects=[s.lower() for s in _list(meta.get("subjects", ""))],
        inputs=_list(meta.get("inputs", "")), output=meta.get("output", "note"),
        output_folder=meta.get("output_folder", ""), filename=meta.get("filename", "{term}.md"),
        expect=meta.get("expect", ""), reset_after=int(meta.get("reset_after", 30)),
        chunk_words=int(cw) if cw not in (None, "") else None,
        prompt=msgs[0], next=msgs[1:], followup=follow.strip())


def load_all(folder: Path):
    out = {}
    for f in sorted(folder.glob("*.md")):
        try:
            r = parse(f.read_text("utf-8"))
            out[r.name] = r
        except Exception as e:
            print(f"[recipes] skipped {f.name}: {e}")
    return out


def expand(t):
    """{{file:prompts/tutor.md}} -> contents of that file (relative to the JARVIS folder)."""
    def grab(m):
        f = ROOT / m.group(1).strip()
        if not f.is_file():
            raise FileNotFoundError(f"prompt file not found: {f}  (create it and paste your prompt into it)")
        txt = f.read_text("utf-8")
        if "REPLACE-ME-PLACEHOLDER" in txt:
            raise ValueError(f"{f.name} is still the placeholder. Paste your real prompt into {f}")
        return txt.strip()
    return re.sub(r"\{\{file:([^}]+)\}\}", grab, t)


def fill(template, v):
    """Replace {name} only when we know it; other braces are left alone."""
    return re.sub(r"\{(\w+)\}", lambda m: str(v.get(m.group(1), m.group(0))), template)


def score(rec, order):
    o = order.lower()
    return sum(1 for k in rec.keywords if k in o)


def _parent_block(v):
    if v.get("parent_text"):
        return ("\n\n---\nTHIS WORD IS LINKED FROM THE NOTE '{parent_term}'. Use that note as extra context "
                "(and as the lesson context if no lesson text is given):\n{parent_text}")
    return ""


def build_prompt(rec, v):
    """Message 1 + automatic context, so plain prompts work without placeholders."""
    body = expand(rec.prompt)
    if v.get("chunk") and "{chunk}" not in body:
        if int(v.get("total", 1)) > 1:
            body += "\n\nThis is part {part} of {total}. Number lessons starting from {start_lesson}."
        body += "\n\nSOURCE TEXT:\n{chunk}"
    elif v.get("lesson_text") and "{lesson_text}" not in body:
        body += ("\n\n---\nSubject: {subject}\nLesson: {lesson_path}\n"
                 "Heading the term sits under: {heading}\nTerm: {term}\n\n"
                 "LESSON TEXT:\n{lesson_text}")
    elif v.get("term") and "{term}" not in body:
        body += "\n\n" + ("Subject: {subject}\n" if v.get("subject") else "") + "Term: {term}"
    return fill(body + _parent_block(v), v)


def followup_text(rec, v):
    t = expand(rec.followup) if rec.followup else (FOLLOW_PDF if v.get("chunk") else FOLLOW_NOTE)
    return fill(t + _parent_block(v), v)
