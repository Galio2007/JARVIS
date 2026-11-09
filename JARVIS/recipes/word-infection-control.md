name: word-infection-control
description: Word note for Infection Control
triggers: new-empty-note
subjects: infection control
output: note
reset_after: 30
---
{{file:prompts/word-core.md}}

{{file:prompts/word-infection-control.md}}
--- followup ---
New term: {term}
Under heading: {heading}
Same lesson, same rules and same template as before. Reply in exactly the same output format (destination line first, then the frontmatter).
