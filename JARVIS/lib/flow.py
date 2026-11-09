import datetime
import difflib
import os
import re
import shutil
from collections import deque
from pathlib import Path
from .config import load, ROOT
from .memory import Memory
from .recipes import load_all, parse, build_prompt, followup_text, score, fill, expand
from .brain import Brain
from .hands import say, notify, handoff, yes, pick
from . import vault, outputs, cutter
from .watchers import Watcher

RECIPE_SPEC = """Write ONE recipe file for my study assistant. Reply with ONLY the file content: no explanation, no code fence.

Format: header lines, then a line containing only ---, then the prompt.
Header keys:
name: short-kebab-case-name
description: one short sentence (a small AI uses it to choose the recipe)
triggers: comma list from: typed-order, new-pdf, new-empty-note
keywords: comma list of words that appear in typed orders for this task
inputs: names of the blanks, comma separated (e.g. term)
output: note   (one filled note)  or  lessons  (split by === LESSON X START === markers)
output_folder: absolute folder (optional)
filename: {term}.md
reset_after: 30
After the prompt you may add a line "--- followup ---" and a short follow-up prompt for later messages in the same chat.
In the prompt you can use {term} {subject} {lesson_path} {heading} {lesson_text} {chunk}. If you leave them out, the assistant appends the context automatically.

The task I want:
"""


class Jarvis:
    def __init__(self):
        self.cfg = load()
        p = self.cfg["paths"]
        self.notes, self.books = p["notes_dir"], p["books_dir"]
        self.dname = self.cfg["vault"].get("dictionary_dir", "X_Dictionary")
        self.marker = self.cfg["vault"]["stop_marker"]
        self.url, self.browser = self.cfg["chat"]["url"], self.cfg["chat"]["browser"]
        self.mem = Memory()
        self.brain = Brain(self.cfg["ai"]["model"])
        self.queue = deque()
        self.reload()
        self.brain.set_system(self.self_context())
        self.watcher = Watcher(self.cfg, self.mem, self.on_event)

    # ---------- basics ----------
    def reload(self):
        self.recipes = load_all(ROOT / "recipes")
        if hasattr(self, "brain"):
            self.brain.set_system(self.self_context())

    def self_context(self):
        tasks = "; ".join(f"{r.name} ({r.description})" for r in self.recipes.values()) or "none yet"
        return (
            "You are JARVIS, a friendly, concise assistant for a dental student, running locally on "
            "their Linux PC. Chat naturally and answer questions normally, in 1-4 sentences. "
            f"Facts about you: you watch the PDF folder '{self.books}' for new PDFs and the notes folder "
            f"'{self.notes}' for new empty word notes. New items wait in a queue until the user types 'go'. "
            f"You can run these tasks: {tasks}. The user starts a task by describing it normally. "
            "Commands: go, pending, recipes, sweep (queue the empty word notes already in the vault), organise (files finished word notes into the dictionary, by each note's own domain line), status, newrecipe, reload, help, exit. "
            "How-to answers, give exactly these commands: to explain the empty word notes type 'sweep' then 'go'; "
            "to file finished word notes type 'organise'; to see the queue type 'pending'; for the full list type 'help'. "
            "If the user's message is not an exact command you did NOT run anything; never say 'sure, I queued it'. "
            "You never write medical content yourself; a stronger AI in the browser does. "
            "Never claim you did something unless a task actually ran.")

    def cands(self, trigger):
        return [r for r in self.recipes.values() if trigger in r.triggers]

    def start(self):
        self.watcher.start()

    def on_event(self, ev):
        self.queue.append(ev)
        notify(f"New {ev['kind']}: {ev['path'].name}")
        print(f"\n[JARVIS] new {ev['kind']}: {ev['path'].name}  (type 'go' when ready)")

    # ---------- command dispatch ----------
    COMMANDS = ["go", "pending", "recipes", "sweep", "organise", "organize", "status",
                "reload", "newrecipe", "help", "exit", "quit"]

    HELP = """
Commands (type them exactly):
  sweep            find the empty word notes already in your Notes folder and queue them
  go               work through the queue one item at a time (asks before every step)
  pending          show what is waiting in the queue
  organise         file finished word notes into X_Dictionary by their domain line
                   (organise <folder> to scan another folder; Enter = the Notes root)
  recipes          list the tasks I know
  reload           re-read recipes and prompts after you edit them
  newrecipe        teach me a new task (DeepSeek writes the recipe file)
  status           show the folders I watch and my settings
  help             this list
  exit             quit  (Ctrl+C only cancels the current task)

Orders in plain words (I only act if you name a real file):
  make notes from /full/path/lecture.pdf

Usual routine for word notes:   sweep  ->  go        (new ones announce themselves; then just: go)
Usual routine for lectures:     drop the PDF in your books folder, or order it; then: go

While a task runs:
  plan question     y = run | n = cancel/pick another | s = skip
  copy prompt step  Enter = I copied the reply | r = copy my prompt again | x = cancel
  reply cut off     type 'continue' in DeepSeek, copy the new part, press Enter here
"""

    def dispatch(self, msg):
        low = msg.lower()
        if " " not in low and low not in self.COMMANDS:
            close = difflib.get_close_matches(low, self.COMMANDS, n=1, cutoff=0.72)
            if close:
                return say(f"I didn't run anything. Did you mean '{close[0]}'?")
        if low in ("exit", "quit"):
            raise SystemExit
        if low == "go":
            return self.go()
        if low == "pending":
            return [print(f"  {e['kind']}: {e['path']}") for e in self.queue] or print("  nothing")
        if low == "recipes":
            return [print(f"  {r.name}: {r.description}  [{', '.join(r.triggers)}]")
                    for r in self.recipes.values()]
        if low == "reload":
            self.reload(); return say(f"{len(self.recipes)} recipes loaded.")
        if low == "status":
            return self.status()
        if low == "sweep":
            return self.sweep()
        w = msg.split(None, 1)
        if w and w[0].lower() in ("organise", "organize"):
            return self.organise(w[1] if len(w) > 1 else "")
        if low == "newrecipe":
            return self.new_recipe()
        if low == "help":
            return print(self.HELP)
        self.order(msg)

    def status(self):
        print(f"  PDF folder : {self.books}  ({'ok' if self.books.is_dir() else 'NOT FOUND'})")
        print(f"  Notes      : {self.notes}  ({'ok' if self.notes.is_dir() else 'NOT FOUND'})")
        print(f"  Dictionary : {self.dict_root()}  ({'ok' if self.dict_root().is_dir() else 'NOT FOUND'})")
        print(f"  Watcher    : {'running' if self.watcher.is_alive() else 'stopped'}, "
              f"{len(self.watcher.known)} files marked as seen")
        print(f"  Pending    : {len(self.queue)}")
        print(f"  Recipes    : {', '.join(self.recipes) or 'none'}")
        print(f"  Model      : {self.cfg['ai']['model']}")

    # ---------- the decision step ----------
    def decide(self, cands, rec, make_plan, allow_chat=False):
        """Show the plan; y runs it, n picks another recipe (or just chats), s skips.
        Returns the recipe, None (skip) or 'chat'."""
        while True:
            if rec is None:
                i = pick([f"{c.name}: {c.description}" for c in cands], "Choose a recipe:")
                if i is None:
                    return None
                rec = cands[i]
            print("\n" + make_plan(rec))
            if allow_chat:
                a = input("Run this? [y = yes | n = no, just talk | p = pick another recipe | s = skip] > ").strip().lower()
                if a == "n":
                    return "chat"
            else:
                a = input("Run this? [y = yes | n = pick another recipe | s = skip] > ").strip().lower()
            if a == "y":
                return rec
            if a == "s":
                return None
            rec = None

    # ---------- typed orders ----------
    def order(self, msg):
        """Chat by default. A task starts only when a recipe keyword hits AND the message
        really contains what that recipe needs (e.g. an existing PDF path)."""
        cands = self.cands("typed-order")
        low = msg.lower()
        rec = next((r for r in cands if low.startswith(r.name.lower())), None)   # "study-notes ~/x.pdf ..."
        if rec is None:
            ranked = sorted(cands, key=lambda r: -score(r, msg))
            s0 = score(ranked[0], msg) if ranked else 0
            top = [r for r in ranked if score(r, msg) == s0] if s0 > 0 else []
            if len(top) == 1:
                rec = top[0]
            elif len(top) > 1:
                rec = self.brain.guess(msg, top)
        vars0 = self.extract_inputs(msg, rec) if rec else None
        if rec is None or vars0 is None:
            return say(self.brain.chat(msg))
        state = {"rec": rec.name, "vars": vars0}

        def plan(r):
            if state["rec"] != r.name:
                state["rec"], state["vars"] = r.name, self.extract_inputs(msg, r)
            v = state["vars"]
            if v is None:
                return f"(I can't find what '{r.name}' needs in your message: {', '.join(r.inputs) or 'a term'})"
            return (f"Plan: recipe '{r.name}'\n  inputs: {v}\n  output: {r.output}"
                    f" -> {self.target_for(r, v)}")

        rec = self.decide(cands, rec, plan, allow_chat=True)
        if rec == "chat":
            return say(self.brain.chat(msg))
        if rec is None:
            return
        v = state["vars"]
        if v is None:
            return say("I'm missing something for that recipe; say it again with the details.")
        if rec.output in ("lessons", "files") and not v.get("out_dir"):
            out = self.ask_folder("Where should the notes go?")
            if out is None:
                return
            v["out_dir"] = str(out)
        key = f"typed::{rec.name}::{v.get('pdf_path', '')}"
        self.execute(rec, v, key, v.get("term") or v.get("pdf_path", rec.name))

    def extract_inputs(self, msg, rec):
        """Fill the recipe's blanks from the message. None = the message doesn't contain them."""
        names = rec.inputs or ["term"]
        parts = [x.strip().strip('"') for x in self.brain.extract(msg).split("|")]
        v = {}
        for i, n in enumerate(names):
            val = parts[i] if i < len(parts) else ""
            if "dir" in n:                      # folders are asked for later if missing
                val = os.path.expanduser(val)
                v[n] = val if (not val or os.path.isabs(val)) else str(self.notes / val)
                continue
            if not val:
                return None
            if "pdf" in n and not Path(val).expanduser().is_file():
                return None
            if n == "term" and len(val.split()) > 8:
                return None
            v[n] = os.path.expanduser(val) if "path" in n else val
        return v

    def target_for(self, rec, v):
        if rec.output in ("lessons", "files"):
            return v.get("out_dir") or rec.output_folder or "(I'll ask you for the folder)"
        from .recipes import fill
        return str(Path(rec.output_folder or self.notes / "JARVIS_inbox") / fill(rec.filename, v))

    # ---------- the pending queue ----------
    def go(self):
        if not self.queue:
            return say("Nothing pending.")
        while self.queue:
            ev = self.queue.popleft()
            if ev["kind"] == "note":
                self.handle_note(ev)
            else:
                batch = [ev] + [e for e in list(self.queue) if e["kind"] == "pdf"]
                for e in batch[1:]:
                    self.queue.remove(e)
                self.handle_pdfs(batch)
            if self.queue and not yes(f"{len(self.queue)} more pending. Continue?"):
                break

    # ---------- PDFs ----------
    def handle_pdfs(self, batch):
        if len(batch) > 1:
            print(f"{len(batch)} new PDFs:")
            for i, e in enumerate(batch, 1):
                print(f"  {i}) {e['path'].relative_to(self.books)}")
            a = input("Process which? (e.g. 1,3 | all | Enter = skip all) > ").strip().lower()
            if a == "all":
                chosen = batch
            else:
                idx = {int(x) - 1 for x in a.replace(" ", "").split(",") if x.isdigit()}
                chosen = [batch[i] for i in sorted(idx) if 0 <= i < len(batch)]
        else:
            chosen = batch
        for e in chosen:
            self.handle_pdf(e)

    def ask_folder(self, q):
        last = self.mem.d.get("last_out", "")
        a = input(f"{q}\n  folder (relative to Notes, or full path | s = skip)"
                  f"{' | Enter = ' + last if last else ''} > ").strip().strip('"')
        if a.lower() == "s":
            return None
        a = a or last
        if not a:
            return None
        f = Path(a).expanduser()
        f = f if f.is_absolute() else self.notes / f
        if not f.exists() and not yes(f"  {f} doesn't exist. Create it when saving?"):
            return None
        self.mem.d["last_out"] = str(f)
        self.mem.save()
        return f

    def handle_pdf(self, ev):
        pdf = ev["path"]
        if not pdf.exists():
            return
        rel = pdf.relative_to(self.books)
        cands = self.cands("new-pdf")
        if not cands:
            return say("No recipe has the 'new-pdf' trigger.")
        out = self.ask_folder(f"New PDF: {rel}\nWhere should its notes go?")
        if out is None:
            return
        v = {"pdf_path": str(pdf), "pdf_name": pdf.name, "rel_path": str(rel.parent),
             "out_dir": str(out)}
        rec = cands[0] if len(cands) == 1 else self.brain.guess(f"{rel}", cands)

        def plan(r):
            saved = self.mem.chat(f"pdf::{rel}::{r.name}")
            return (f"Plan: recipe '{r.name}' on {rel}\n  output: {r.output} -> {out}"
                    f"\n  chat: {'saved chat exists' if saved else 'new chat'}"
                    f"{' | ' + str(1 + len(r.next)) + ' messages in one chat' if r.next else ''}")

        rec = self.decide(cands, rec, plan)
        if rec and self.execute(rec, v, f"pdf::{rel}::{rec.name}", pdf.stem):
            self.watcher.done(pdf)

    # ---------- unknown-word notes ----------
    def subject_dirs(self):
        wanted = [x.casefold() for x in self.cfg["vault"].get("subjects", [])]
        if wanted:
            return [d.name for d in sorted(self.notes.iterdir()) if d.is_dir() and d.name.casefold() in wanted]
        return [d.name for d in sorted(self.notes.iterdir())
                if d.is_dir() and not d.name.startswith(".") and d.name.casefold() != self.dname.casefold()]

    def ask_subject(self, term):
        subs = self.subject_dirs()
        i = pick(subs, f"Which subject is '{term}' for?")
        return None if i is None else subs[i]

    def dict_root(self):
        for d in self.notes.iterdir():
            if d.is_dir() and d.name.casefold() == self.dname.casefold():
                return d
        return self.notes / self.dname

    def ask_domain(self, f):
        doms = vault.domains(self.dict_root())
        print(f"\n{f.name}: no '[Folder Destination: ...]' or 'domain:' line in it.")
        for i, d in enumerate(doms, 1):
            print(f"  {i}) {d}")
        a = input("  number, or type a new domain name (Enter = skip) > ").strip()
        if not a:
            return None
        if a.isdigit() and 1 <= int(a) <= len(doms):
            return doms[int(a) - 1]
        return re.sub(r'[\\/:*?"<>|]', "", a).strip() or None

    def _move(self, p, domain):
        """Move a note into <dictionary>/<domain>/. Never overwrites. -> (status, dest)"""
        d = self.dict_root() / domain
        dest = d / p.name
        if p.parent == d:
            return "already", dest
        if dest.exists():
            return "exists", dest
        d.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dest))
        return "moved", dest

    def file_away(self, p):
        """File a finished note by its own domain line; ask if it has none."""
        domain = vault.read_domain(p.read_text("utf-8", errors="ignore")) or self.ask_domain(p)
        if not domain:
            say(f"{p.name} left where it is.")
            return p
        st, dest = self._move(p, domain)
        say({"moved": f"Filed: {self.dname}/{domain}/{p.name}",
             "already": f"{p.name} is already in {domain}.",
             "exists": f"{p.name} already exists in {self.dname}/{domain}; left where it is."}[st])
        return dest if st == "moved" else p

    def locate(self, term, p):
        """-> (subject, lesson ctx) or None. The linking lesson tells us the subject."""
        ctx = self.pick_lesson(term, self.notes)
        if ctx is None:
            return None
        parts = Path(ctx["lesson_key"]).parts if ctx.get("lesson_key") else ()
        subject = parts[0] if len(parts) > 1 else self.ask_subject(term)
        return None if subject is None else (subject, ctx)

    def organise(self, arg=""):
        """File finished (non-empty) word notes into <dictionary>/<domain>, using each note's own
        '[Folder Destination: X]' line or YAML 'domain:' (same rule as your old script)."""
        folder = None
        if arg.strip():
            f = Path(arg.strip().strip('"')).expanduser()
            f = f if f.is_absolute() else self.notes / f
            folder = f if f.is_dir() else None
        if folder is None:
            a = input("Which folder holds the notes to organise?\n  (Enter = the Notes root, files directly "
                      "inside it | or a relative/full path) > ").strip().strip('"')
            f = Path(a).expanduser() if a else self.notes
            folder = f if f.is_absolute() else self.notes / f
        if not folder.is_dir():
            return say(f"No such folder: {folder}")
        if vault.in_dictionary(folder / "x.md", self.notes, self.dname):
            return say(f"That folder is already inside {self.dname}.")
        files = sorted(f for f in folder.glob("*.md") if not f.name.startswith("."))
        empties = [f for f in files if vault.is_empty_note(f)]
        files = [f for f in files if f not in empties]
        if not files:
            return say(f"No finished notes directly inside {folder}"
                       f"{f' ({len(empties)} empty ones skipped)' if empties else ''}.")
        ready, unsure = [], []
        for f in files:
            dom = vault.read_domain(f.read_text("utf-8", errors="ignore"))
            (ready if dom else unsure).append((f, dom))
        moved, skipped, clashes = 0, 0, []

        def do(f, domain):
            nonlocal moved, skipped
            st, dest = self._move(f, domain)
            if st == "moved":
                moved += 1; print(f"  moved: {f.name} -> {self.dname}/{domain}")
            else:
                skipped += 1
                if st == "exists":
                    clashes.append(f"{f.name} (already in {self.dname}/{domain})")

        if ready:
            root = self.dict_root()
            print(f"\nReady to move ({len(ready)}):")
            for f, dom in ready:
                print(f"  {f.name}  ->  {self.dname}/{dom}{'' if (root / dom).is_dir() else '  (new folder)'}")
            a = input("Move these? [y = all | r = review one by one | n = skip these] > ").strip().lower()
            if a == "y":
                for f, dom in ready:
                    do(f, dom)
            elif a == "r":
                rest = False
                for f, dom in ready:
                    b = "y" if rest else input(f"  {f.name} -> {dom}  "
                                               "[y | s = skip | a = yes to all the rest | q = stop] > ").strip().lower()
                    if b == "q":
                        break
                    if b == "a":
                        rest = True; b = "y"
                    if b == "y":
                        do(f, dom)
                    else:
                        skipped += 1
            else:
                skipped += len(ready)
        for f, _ in unsure:
            dom = self.ask_domain(f)
            if dom:
                do(f, dom)
            else:
                skipped += 1
        say(f"Done. Moved {moved}, skipped {skipped}"
            f"{f', {len(empties)} empty notes ignored' if empties else ''}.")
        if clashes:
            print("  Not moved because a note with that name already exists there:")
            for c in clashes:
                print(f"   - {c}")

    def tidy_note(self, reply):
        """Drop the code fence and the '[Folder Destination: X]' line (when the YAML 'domain:' keeps
        the info) so the frontmatter starts the file and Obsidian reads it as properties."""
        t = outputs.strip_fence(reply).strip()
        m = re.match(r"\[Folder Destination:[^\]]*\][ \t]*\n", t, re.I)
        if m and re.search(r"^domain:\s*\S", t, re.M | re.I):
            t = t[m.end():].lstrip("\n")
        t = re.sub(r"\A---[ \t]*\n(?=---[ \t]*\n)", "", t)
        return t

    def sweep(self):
        """Queue the empty word notes that already sit in the Notes root (the watcher only sees new ones)."""
        found, orphans = [], []
        for f in sorted(self.notes.glob("*.md")):
            if f.name.startswith(".") or not vault.is_empty_note(f) or str(f) in self.watcher.queued:
                continue
            (found if vault.has_backlink(f.stem, self.notes, self.dname, self.watcher.only) else orphans).append(f)
        for f in found:
            self.watcher.queued.add(str(f))
            self.queue.append({"kind": "note", "path": f})
        say(f"Queued {len(found)} empty word notes" + (": " + ", ".join(f.stem for f in found) if found else "")
            + (". Type 'go' to start." if found else "."))
        if orphans:
            print("  Not queued (no lesson links to them): " + ", ".join(f.stem for f in orphans))

    def handle_note(self, ev):
        p = ev["path"]
        if not p.exists() or not vault.is_empty_note(p):
            return self.watcher.done(p)
        term = p.stem
        loc = self.locate(term, p)
        if loc is None:
            return
        subject, ctx = loc
        dup = vault.find_in_dictionary(term, self.dict_root())
        if dup and dup != p:
            a = input(f"'{term}' is already explained in {dup.parent.name}/. "
                      "[s] skip (the empty duplicate stays for you to delete) | "
                      "[n] explain it again anyway > ").strip().lower()
            if a != "n":
                return
        v = {"term": term, "subject": subject, **ctx,
             "domains": ", ".join(vault.domains(self.dict_root())) or "(none yet)",
             "today": datetime.date.today().isoformat()}
        cands = [r for r in self.cands("new-empty-note")
                 if not r.subjects or subject.casefold() in r.subjects]
        cands = [r for r in cands if r.subjects] or cands     # a subject-specific recipe beats a general one
        if not cands:
            return say(f"No recipe fits a new note in '{subject}' "
                       "(trigger 'new-empty-note', matching 'subjects:').")
        hint = f"{term} (heading: {v.get('heading', '')})"
        rec = cands[0] if len(cands) == 1 else self.brain.guess(hint, cands)

        def plan(r):
            k = f"{v.get('lesson_key', term)}::{r.name}"
            sv = self.mem.chat(k)
            return (f"Plan: recipe '{r.name}'\n  term: {term} | subject: {subject}\n"
                    f"  lesson: {v.get('lesson_path') or '(none)'}"
                    f" | heading: {v.get('heading') or '-'}\n"
                    f"{'  via: linked from the dictionary note ' + repr(v['via']) + chr(10) if v.get('via') else ''}"
                    f"  chat: {'saved chat exists (' + str(sv['uses']) + ' uses)' if sv else 'new chat'}\n"
                    f"  output: fills {p}\n"
                    f"  then: files it into {self.dname}/<domain named inside the note>")

        rec = self.decide(cands, rec, plan)
        if rec and self.execute(rec, v, f"{v.get('lesson_key', term)}::{rec.name}", term, target=p):
            self.watcher.done(p)
            self.watcher.done(self.file_away(p))

    def via_dictionary(self, term, depth=3, seen=None):
        """The word is linked only from other dictionary notes: follow them up to a lesson.
        Returns a context dict (lesson ctx if one is reachable, plus the parent note), or None."""
        seen = (seen or set()) | {term.casefold()}
        parents = [h for h in vault.find_lessons(term, self.notes, self.dname, include_dictionary=True)
                   if vault.in_dictionary(h[0], self.notes, self.dname)
                   and h[0].stem.casefold() not in seen and not vault.is_empty_note(h[0])]
        if not parents:
            return None
        if len(parents) > 1:
            i = pick([f"{h[0].parent.name}/{h[0].stem}" for h in parents],
                     f"[[{term}]] is linked from several dictionary notes. Which one?")
            if i is None:
                return None
            parents = [parents[i]]
        f, txt, pos = parents[0]
        ctx = {}
        lessons = vault.find_lessons(f.stem, self.notes, self.dname, only=self.watcher.only)
        if lessons:
            i = 0 if len(lessons) == 1 else pick([str(h[0].relative_to(self.notes)) for h in lessons],
                                                  f"The note '{f.stem}' appears in several lessons. Which one?")
            if i is None:
                return None
            ctx = self.lesson_ctx(*lessons[i])
        elif depth > 1:
            deeper = self.via_dictionary(f.stem, depth - 1, seen)
            if deeper:
                ctx = {k: x for k, x in deeper.items() if k not in ("parent_term", "parent_text", "via")}
        ph = vault.heading_before(txt, pos)
        ctx.update({"parent_term": f.stem, "parent_text": txt.strip()[:6000], "via": f.stem,
                    "heading": f"{ph + ' ' if ph else ''}(in the note '{f.stem}')"})
        return ctx

    def pick_lesson(self, term, root):
        hits = vault.find_lessons(term, root, self.dname, only=self.watcher.only if root == self.notes else None)
        if not hits:
            via = self.via_dictionary(term) if root == self.notes else None
            if via is not None:
                return via
            a = input(f"No lesson links to [[{term}]]. [p] give a lesson path | "
                      "[n] no context | [s] skip > ").strip().lower()
            if a == "n":
                return {}
            if a != "p":
                return None
            f = Path(input("  lesson file > ").strip().strip('"')).expanduser()
            f = f if f.is_absolute() else self.notes / f
            if not f.is_file():
                say("File not found."); return None
            return self.lesson_ctx(f, f.read_text("utf-8", errors="ignore"), 0)
        if len(hits) == 1:
            return self.lesson_ctx(*hits[0])
        i = pick([str(h[0].relative_to(self.notes)) for h in hits],
                 f"[[{term}]] appears in several lessons. Which one?")
        return None if i is None else self.lesson_ctx(*hits[i])

    def lesson_ctx(self, f, txt, pos):
        rel = f.relative_to(self.notes)
        return {"lesson_file": str(f), "lesson_key": str(rel.with_suffix("")),
                "lesson_path": " / ".join(rel.parent.parts[1:]) or rel.parent.name,
                "heading": vault.heading_before(txt, pos),
                "lesson_text": vault.cut_at(txt, self.marker)}

    # ---------- running a recipe ----------
    def execute(self, rec, v, key, label, target=None):
        try:
            if rec.output in ("lessons", "files"):
                return self.run_lessons(rec, v, key, label)
            reply = self.exchange(rec, key, v, label)
            if reply is None:
                return False
            from .recipes import fill
            path = target or Path(rec.output_folder or self.notes / "JARVIS_inbox") / fill(rec.filename, v)
            outputs.save_note(path, self.tidy_note(reply) if target else reply)
            say(f"Saved: {path}")
            return True
        except Exception as e:
            say(f"Failed: {e}")
            return False

    def pipeline(self, rec, v, label):
        """Several messages in ONE new chat (e.g. tutor, then splitter). Returns the last reply."""
        msgs = [build_prompt(rec, v)] + [fill(expand(m), v) for m in rec.next]
        url, linked, reply = self.url, False, None
        for i, m in enumerate(msgs, 1):
            last = i == len(msgs)
            hint = ""
            if i > 1:
                hint = ("Paste into THIS chat (opened for you)." if linked else
                        "Paste into the SAME chat as the previous step.")
            reply = handoff(m, url, f"{label} · message {i}/{len(msgs)}", self.browser,
                            rec.expect if last else "", cont=linked, hint=hint)
            if reply is None:
                return None
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:40]
            (ROOT / "work" / f"{safe}_msg{i}.md").write_text(reply, "utf-8")
            if i == 1 and not last:
                link = input("Paste this chat's link from the address bar (Enter = skip) > ").strip()
                if link.startswith("http"):
                    url, linked = link, True
        return reply

    def exchange(self, rec, key, v, label, force=False):
        if rec.next:
            return self.pipeline(rec, v, label)
        saved = self.mem.chat(key)
        cont = False
        if saved:
            if saved["uses"] >= rec.reset_after:
                say(f"That chat has {saved['uses']} uses, so I'll start a fresh one.")
            elif force or yes(f"Saved chat for '{label}' ({saved['uses']} uses). Continue it?"):
                cont = True
        payload = followup_text(rec, v) if cont else build_prompt(rec, v)
        url = saved["url"] if cont else self.url
        reply = handoff(payload, url, f"{label} · {rec.name}", self.browser, rec.expect, cont)
        if reply is None:
            return None
        if cont:
            self.mem.bump(key)
        else:
            link = input("Paste this chat's link from the address bar (Enter = skip) > ").strip()
            if link.startswith("http"):
                self.mem.set_chat(key, link)
        return reply

    def run_lessons(self, rec, v, key, label):
        pdf = Path(v["pdf_path"]).expanduser()
        out_dir = Path(v.get("out_dir") or rec.output_folder or self.notes / pdf.stem).expanduser()
        v = {**v, "pdf_name": pdf.name, "out_dir": str(out_dir)}
        text = outputs.convert_pdf(pdf, ROOT / "work")          # BMO
        cw = rec.chunk_words if rec.chunk_words is not None else self.cfg["pdf"]["chunk_words"]
        words = len(text.split())
        if cw == 0:
            parts = [text]
            if words > 15000 and not yes(f"This PDF has {words} words; one paste may be too big "
                                         "for DeepSeek. Send it whole anyway?"):
                return False
        else:
            parts = outputs.chunk(text, cw)
        full, n = [], 1
        for i, c in enumerate(parts, 1):
            pv = {**v, "chunk": c, "part": i, "total": len(parts), "start_lesson": n}
            lab = f"{label} part {i}/{len(parts)}" if len(parts) > 1 else label
            reply = self.exchange(rec, key, pv, lab, force=i > 1)
            if reply is None:
                say("Cancelled. Anything done so far is in work/.")
                break
            (ROOT / "work" / f"{pdf.stem}_final{i}.md").write_text(reply, "utf-8")
            full.append(reply)
            nums = [int(x) for x in outputs.START.findall(reply)]
            n = max(nums) + 1 if nums else n
        if not full:
            return False
        joined = "\n".join(full)
        if rec.output == "files":                                 # Rattleballs
            res = cutter.cut(joined, out_dir, self.notes, ROOT / "work" / "backups")
            for name, backed in res["created"]:
                print(f"  created: {name}{'  (old version backed up in work/backups)' if backed else ''}")
            print(f"\n{len(res['created'])} files -> {res['target']}")
            for n in res["notes"]:
                print(f"  note: {n}")
            if res["review"]:
                print(f"  {len(res['review'])} files contain 'Review needed': " + ", ".join(res["review"]))
            if res["problems"]:
                print(f"\n{len(res['problems'])} problem(s):")
                for pr in res["problems"]:
                    print(" -", pr)
            if res["incomplete"]:
                say("The reply looks incomplete; check the problems above.")
            return bool(res["created"])
        files = outputs.split_lessons(joined, out_dir)
        say(f"Created {len(files)} lesson files in {out_dir}")
        return bool(files)

    # ---------- teaching JARVIS a new task ----------
    def new_recipe(self):
        desc = input("Describe the new task in plain words > ").strip()
        if not desc:
            return
        reply = handoff(RECIPE_SPEC + desc, self.url, "new recipe", self.browser, r"\n---\n")
        if reply is None:
            return
        text = outputs.strip_fence(reply)
        try:
            rec = parse(text)
        except Exception as e:
            (ROOT / "work" / "failed_recipe.txt").write_text(text, "utf-8")
            return say(f"That wasn't a valid recipe ({e}). Saved to work/failed_recipe.txt")
        f = ROOT / "recipes" / f"{rec.name}.md"
        if f.exists() and not yes(f"{f.name} exists. Overwrite?"):
            return
        f.write_text(text + "\n", "utf-8")
        self.reload()
        say(f"Recipe '{rec.name}' saved to {f}")
