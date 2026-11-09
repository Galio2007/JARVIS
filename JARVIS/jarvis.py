#!/usr/bin/env python3
from lib.flow import Jarvis
from lib.hands import say


def main():
    j = Jarvis()
    j.start()
    say(f"Online. {len(j.recipes)} recipes. Type 'help' for commands.")
    while True:
        try:
            n = len(j.queue)
            msg = input(f"[{n} pending] You: " if n else "You: ").strip()
        except EOFError:
            print(); break
        except KeyboardInterrupt:
            print("\n(Ctrl+C only cancels a task. Type 'exit' to quit.)"); continue
        if not msg:
            continue
        try:
            j.dispatch(msg)
        except SystemExit:
            break
        except KeyboardInterrupt:
            print()
            say("Cancelled. The notes are still empty, so 'sweep' then 'go' will pick them up again.")
        except Exception as e:
            say(f"Error: {e}")
    say("Bye.")


if __name__ == "__main__":
    main()
