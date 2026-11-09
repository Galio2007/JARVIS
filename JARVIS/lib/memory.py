import json
from .config import ROOT

FILE = ROOT / "memory.json"


class Memory:
    """chats: key -> {url, uses}.  known: files already seen (None = first run)."""

    def __init__(self):
        self.d = json.loads(FILE.read_text("utf-8")) if FILE.exists() else {}
        self.d.setdefault("chats", {})
        self.d.setdefault("known", None)

    def save(self):
        FILE.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), "utf-8")

    def chat(self, key):
        return self.d["chats"].get(key)

    def set_chat(self, key, url):
        self.d["chats"][key] = {"url": url, "uses": 1}
        self.save()

    def bump(self, key):
        if key in self.d["chats"]:
            self.d["chats"][key]["uses"] += 1
            self.save()

    def forget_chat(self, key):
        self.d["chats"].pop(key, None)
        self.save()
