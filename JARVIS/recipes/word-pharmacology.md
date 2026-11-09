name: word-pharmacology
description: Word note for Pharmacology
triggers: new-empty-note
subjects: pharmacology
output: note
reset_after: 30
---
{{file:prompts/word-core.md}}

{{file:prompts/word-pharmacology.md}}
--- followup ---
New term: {term}
Under heading: {heading}
Same lesson, same rules and same template as before. Reply in exactly the same output format (destination line first, then the frontmatter).
