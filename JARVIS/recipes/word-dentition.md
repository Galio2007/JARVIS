name: word-dentition
description: Word note for Dentition
triggers: new-empty-note
subjects: dentition
output: note
reset_after: 30
---
{{file:prompts/word-core.md}}

{{file:prompts/word-dentition.md}}
--- followup ---
New term: {term}
Under heading: {heading}
Same lesson, same rules and same template as before. Reply in exactly the same output format (destination line first, then the frontmatter).
