import os
import threading
import time
from pathlib import Path
from . import vault


class Watcher(threading.Thread):
    """Polls the books folder (PDFs) and the vault (new empty notes in *_Dictionary)."""

    def __init__(self, cfg, mem, on_event):
        super().__init__(daemon=True)
        self.books, self.notes = cfg["paths"]["books_dir"], cfg["paths"]["notes_dir"]
        self.dname = cfg["vault"].get("dictionary_dir", "X_Dictionary")
        self.every = cfg["watch"]["interval_seconds"]
        self.only = {x.casefold() for x in cfg["vault"].get("subjects", [])} or None
        self.mem, self.on_event = mem, on_event
        self.first = mem.d["known"] is None
        self.known = set(mem.d["known"] or [])
        self.sizes, self.queued = {}, set()
        self.lock = threading.Lock()

    def scan(self):
        for base, kind, ext in ((self.books, "pdf", ".pdf"), (self.notes, "note", ".md")):
            if not base.is_dir():
                continue
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in files:
                    if f.lower().endswith(ext):
                        yield kind, Path(root) / f

    def _save(self):
        with self.lock:
            self.mem.d["known"] = sorted(self.known)
            self.mem.save()

    def done(self, path):
        with self.lock:
            self.known.add(str(path))
        self._save()

    def tick(self):
        n0 = len(self.known)
        for kind, p in list(self.scan()):
            s = str(p)
            if s in self.known or s in self.queued:
                continue
            if self.first:
                self.known.add(s); continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if self.sizes.get(s) != size or (kind == "pdf" and size == 0):
                self.sizes[s] = size      # still being written; wait one more scan
                continue
            if kind == "note":
                # an unknown-word note = empty AND some lesson links to it (anywhere in the vault)
                ok = vault.is_empty_note(p) and (vault.in_dictionary(p, self.notes, self.dname)
                                                 or vault.has_backlink(p.stem, self.notes, self.dname, self.only))
                if not ok:
                    self.known.add(s); continue
            self.queued.add(s)
            self.on_event({"kind": kind, "path": p})
        if self.first:
            self.first = False
            print(f"[watch] first run: {len(self.known)} existing files marked as seen")
        if len(self.known) != n0:
            self._save()

    def run(self):
        while True:
            try:
                self.tick()
            except Exception as e:
                print(f"[watch] error: {e}")
            time.sleep(self.every)
