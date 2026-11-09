import re
import shutil
import subprocess
import webbrowser
import pyperclip


def say(msg):
    print(f"JARVIS: {msg}")


def notify(msg):
    if shutil.which("notify-send"):
        subprocess.Popen(["notify-send", "JARVIS", msg])


def open_url(url, browser=""):
    exe = shutil.which(browser) if browser else None
    cmd = [exe, url] if exe else ["xdg-open", url]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except Exception:
        webbrowser.open(url)


def yes(q):
    return input(f"{q} [y/n] > ").strip().lower() in ("y", "yes")


def pick(options, title):
    """Numbered list. Returns index, or None for cancel."""
    print(title)
    for i, o in enumerate(options, 1):
        print(f"  {i}) {o}")
    a = input("  number (Enter = cancel) > ").strip()
    return int(a) - 1 if a.isdigit() and 1 <= int(a) <= len(options) else None


def handoff(payload, url, label, browser, expect="", cont=False, hint=""):
    """Copy payload, open DeepSeek, wait for the copied reply. None = cancelled.
    If `expect` is missing (reply cut off), the user can say 'continue' in DeepSeek
    and the next copied reply is appended."""
    pyperclip.copy(payload)
    open_url(url, browser)
    print(f"\n[clipboard ready] {label}")
    if hint:
        print(f"  1) {hint}")
    elif cont:
        print(f"  1) Paste into THIS saved chat (opened for you): {url}")
    else:
        print(f"  1) Start a NEW chat at {url} and paste. Name it: {label}")
    print("  2) When the reply finishes, press its Copy button")
    print("  3) Back here: Enter = I copied it | r = re-copy my prompt | x = cancel")
    acc, last = "", ""
    while True:
        a = input("  > ").strip().lower()
        if a == "x":
            return None
        if a == "r":
            pyperclip.copy(payload); open_url(url, browser); continue
        if a == "m" and acc:
            return acc
        reply = pyperclip.paste()
        if reply.strip() in (payload.strip(), last.strip()):
            print("  Clipboard has nothing new; copy the reply first."); continue
        acc = acc + ("\n" if acc else "") + reply
        last = reply
        if not expect or re.search(expect, acc):
            return acc
        print("  The reply looks cut off (end marker missing). In DeepSeek type: continue")
        print("  then copy the new reply and press Enter. (m = use what I have | x = cancel)")
