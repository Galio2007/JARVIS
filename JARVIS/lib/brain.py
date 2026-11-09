import re
import ollama

SYSTEM = ("You are JARVIS, a concise, witty assistant for a dental student. "
          "Reply in 1-3 sentences.")

EXTRACT = """Extract the main input from the order. Reply with only the input, nothing else.

Order: I don't get what pheochromocytoma is, add it to obsidian
Input: pheochromocytoma

Order: explain myasthenia gravis for my notes
Input: myasthenia gravis

Order: make notes from ~/Downloads/anatomy3.pdf into ~/Notes/Anatomy
Input: ~/Downloads/anatomy3.pdf | ~/Notes/Anatomy

Order: what does Cushing syndrome mean, put it in obsidian
Input: Cushing syndrome

Order: """

GUESS = """Pick the number of the task that best matches the order. Reply with only the number. Reply 0 if none fit.

Example tasks:
1. cooking-recipe: give a recipe for a dish
2. translate: translate text into another language
Order: how do I make pancakes
Answer: 1
Order: say hello in French
Answer: 2
Order: what is the capital of Peru
Answer: 0

Now the real one.
Tasks:
"""


class Brain:
    """Qwen: chats, extracts the blank from an order, guesses a recipe. Writes no content."""

    def __init__(self, model):
        self.model = model
        self.history = [{"role": "system", "content": SYSTEM}]

    def set_system(self, text):
        self.history[0] = {"role": "system", "content": text}

    def _call(self, messages, temp=0):
        try:
            r = ollama.chat(model=self.model, messages=messages, options={"temperature": temp})
        except Exception as e:
            raise RuntimeError(f"Ollama not reachable ({e}). Try: sudo systemctl start ollama")
        return r["message"]["content"].strip()

    def extract(self, order):
        out = self._call([{"role": "user", "content": EXTRACT + order + "\nInput:"}])
        return out.splitlines()[0].strip() if out else ""

    def guess(self, order, recipes):
        menu = "\n".join(f"{i}. {r.name}: {r.description}" for i, r in enumerate(recipes, 1))
        out = self._call([{"role": "user", "content": f"{GUESS}{menu}\nOrder: {order}\nAnswer:"}])
        m = re.search(r"\d+", out)
        n = int(m.group()) if m else 0
        return recipes[n - 1] if 1 <= n <= len(recipes) else None

    def chat(self, text):
        self.history.append({"role": "user", "content": text})
        reply = self._call([self.history[0]] + self.history[-11:], temp=0.6)
        self.history.append({"role": "assistant", "content": reply})
        return reply
