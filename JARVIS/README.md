# JARVIS

Run:  source venv/bin/activate.fish && python jarvis.py
Commands: go | pending | recipes | reload | newrecipe | help | exit  (anything else = an order or chat)

## Folders
- recipes/   one .md per task. Header, a line with only ---, message 1,
             optional `--- next ---` + message 2 (same chat), optional `--- followup ---`.
- prompts/   YOUR prompt files (tutor.md, splitter.md). Recipes load them with {{file:prompts/tutor.md}}.
- config.toml  folders, model, browser, stop word
- memory.json  saved chat links per lesson, files already seen
- work/      extracted PDF text and every reply (backup)

## Recipe header keys
name, description, triggers (typed-order, new-pdf, new-empty-note), keywords,
subjects (e.g. Physics, Biology; empty = all), inputs, output (note | files),
output_folder, filename, expect (regex the last reply must contain),
chunk_words (0 = send whole PDF), reset_after.

## One prompt per subject
Make one recipe per subject for new-empty-note and set `subjects:`.
A new empty note in Physics_Dictionary only uses recipes listing physics (or no subjects).
