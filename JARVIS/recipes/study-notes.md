name: study-notes
description: Turn a lecture PDF into a connected Obsidian note system
triggers: typed-order, new-pdf
keywords: pdf, notes from, convert, make notes
inputs: pdf_path | out_dir
output: files
chunk_words: 0
expect: ALL FILES DONE
---
{{file:prompts/tutor.md}}
--- next ---
{{file:prompts/splitter.md}}
