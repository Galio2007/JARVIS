"""Rattleballs: cut an AI '= FILE START: name = ... = FILE END =' reply into Obsidian notes.
Ported from the user's split_deepseek.py (same fixes and checks), made callable from JARVIS."""
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

START = re.compile(r"^\s*=+\s*FILE START:\s*(.+?)\s*=*\s*$", re.I)
END = re.compile(r"^\s*=+\s*FILE END\s*=+\s*$", re.I)
DONE = re.compile(r"^\s*=+\s*ALL FILES DONE\s*=+\s*$", re.I)
BAD_CHARS = re.compile(r'[\\/*?"<>|#^\[\]]')
CARD_LINE = re.compile(r"^---card---( \?type)? \^([a-z0-9][a-z0-9-]*)\s*$")
CLOZE_ID = re.compile(r"==c\d+::.*\^([a-z0-9][a-z0-9-]*)\s*$")


# ---------- parsing ----------
def parse(text):
    files, cur, buf, problems, done = [], None, [], [], False
    for line in text.splitlines():
        m = START.match(line)
        if m:
            if cur is not None:
                problems.append(f"'{cur}' has no FILE END (cut off?) - skipped")
            cur, buf = m.group(1), []
            continue
        if cur is not None and END.match(line):
            files.append((cur, "\n".join(buf)))
            cur = None
            continue
        if DONE.match(line):
            done = True
            continue
        if cur is not None:
            buf.append(line)
    if cur is not None:
        problems.append(f"'{cur}' has no FILE END (cut off?) - skipped")
    return files, problems, done


def clean_name(raw):
    name = Path(raw.strip().replace("\\", "/")).name
    name = name.replace(":", " -")
    name = BAD_CHARS.sub("", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name.lower().endswith((".md", ".canvas")):
        name += ".md"
    return name


# ---------- auto-fixes for common model slips ----------
def unwrap(body, langs="markdown|md"):
    lines = body.strip("\n").split("\n")
    if (len(lines) >= 2 and re.match(rf"^```({langs})?\s*$", lines[0])
            and lines[-1].strip() == "```"):
        lines = lines[1:-1]
    return "\n".join(lines).strip("\n")


def fix_frontmatter(body):
    if not body.startswith("---\n"):
        return body
    end = body.find("\n---", 4)
    if end == -1:
        return body
    fm, rest = body[:end], body[end:]
    fm = re.sub(r"^(parent:\s*)(\[\[.*?\]\])\s*$", r'\1"\2"', fm, flags=re.M)
    fm = re.sub(r"^(tags:\s*)(\[.*\])\s*$",
                lambda m: m.group(1) + m.group(2).replace("#", ""), fm, flags=re.M)
    return fm + rest


def fix_cards(body):
    body = re.sub(r"^[ \t#>\-]*(---card---)", r"\1", body, flags=re.M)
    body = re.sub(r"(---card---(?: \?type)?)[ \t]*\n\^([a-z0-9-]+)", r"\1 ^\2", body)
    return body


# ---------- validation ----------
def check_quiz(name, body, problems):
    for i, m in enumerate(re.finditer(r"```quizport\n(.*?)\n```", body, re.S), 1):
        raw = m.group(1).strip()
        if raw.startswith("file:"):
            continue
        tag = f"{name}: quizport block {i}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            problems.append(f"{tag} is not valid JSON ({e.msg}, line {e.lineno})")
            continue
        qs = data.get("questions")
        if not data.get("title") or not isinstance(qs, list) or not qs:
            problems.append(f"{tag} needs a title and a non-empty questions list")
            continue
        for n, q in enumerate(qs, 1):
            ch, ans = q.get("choices"), q.get("answer")
            if not q.get("question") or not isinstance(ch, list) or len(ch) < 2:
                problems.append(f"{tag} Q{n}: missing question or choices")
                continue
            idx = ans if isinstance(ans, list) else [ans]
            if not idx or not all(isinstance(a, int) and 0 <= a < len(ch) for a in idx):
                problems.append(f"{tag} Q{n}: answer {ans!r} is not a valid 0-based index")


def check_cards(name, body, seen, problems):
    has_cards = False
    for line in body.splitlines():
        if line.startswith("---card---"):
            has_cards = True
            m = CARD_LINE.match(line)
            if not m:
                problems.append(f"{name}: bad card line -> {line[:50]!r}")
                continue
            cid = m.group(2)
        else:
            m = CLOZE_ID.search(line)
            if not m:
                continue
            has_cards = True
            cid = m.group(1)
        if cid in seen:
            problems.append(f"{name}: duplicate card ID ^{cid} (also in {seen[cid]})")
        seen[cid] = name
    if has_cards:
        fm = body.split("\n---", 1)[0] if body.startswith("---\n") else ""
        if "flashcards" not in fm:
            problems.append(f"{name}: has cards but no 'flashcards' tag in frontmatter")


def check_links(contents, target_dir, problems):
    stems = {Path(n).stem for n in contents}
    if target_dir.exists():
        stems |= {p.stem for p in target_dir.glob("*.md")}
    for name, body in contents.items():
        for m in re.finditer(r"\[\[([^\]|#]+)", body):
            tgt = m.group(1).strip()
            if re.match(r"^\d+(\.\d+)*\s", tgt) and tgt not in stems:
                problems.append(f"{name}: link to missing note [[{tgt}]]")


# ---------- the cut ----------
def cut(text, target: Path, vault_root: Path, backup_root: Path):
    """Write the files declared in `text` into `target` (must be inside `vault_root`).
    Existing files are backed up to backup_root/<timestamp>/ before being replaced.
    Returns {created: [(name, backed_up)], target, problems, notes, review, incomplete}."""
    target = Path(target).expanduser().resolve()
    vault_root = Path(vault_root).resolve()
    if vault_root not in [target, *target.parents]:
        raise ValueError(f"Refusing: {target} is outside the vault {vault_root}")
    files, problems, done = parse(text)
    if not files:
        raise ValueError("No '= FILE START: ... =' blocks found in the reply.")
    if not done:
        problems.append("Missing '=== ALL FILES DONE ===' - the output may be incomplete")

    contents, seen, notes = {}, {}, []
    for raw_name, body in files:
        name = clean_name(raw_name)
        if name.lower().endswith(".canvas"):
            body = unwrap(body, "json|markdown|md")
            try:
                json.loads(body)
            except Exception:
                name = name[:-7] + " (heading tree).md"
                notes.append(f"{name}: was a heading tree, not canvas JSON; saved as .md for Canvas Smart Paste")
            else:
                contents[name] = body
                continue
        else:
            body = unwrap(body)
        body = fix_cards(fix_frontmatter(body))
        if name in contents:
            problems.append(f"{name}: appears twice, the later copy wins")
        contents[name] = body
        if not body.startswith("---\n"):
            problems.append(f"{name}: no YAML frontmatter")
        check_quiz(name, body, problems)
        check_cards(name, body, seen, problems)
    check_links({n: b for n, b in contents.items() if n.endswith(".md")}, target, problems)

    review = [n for n, b in contents.items() if "Review needed" in b]
    backups = Path(backup_root) / datetime.now().strftime("%Y%m%d-%H%M%S")
    target.mkdir(parents=True, exist_ok=True)
    created = []
    for name, body in contents.items():
        path = target / name
        backed = path.exists()
        if backed:
            backups.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backups / name)
        path.write_text(body + "\n", encoding="utf-8")
        created.append((name, backed))
    incomplete = any("no FILE END" in p or "ALL FILES DONE" in p for p in problems)
    return {"created": created, "target": target, "problems": problems, "notes": notes,
            "review": review, "incomplete": incomplete}
