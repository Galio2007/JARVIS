name: word-microbiology
description: Word note for Microbiology
triggers: new-empty-note
subjects: microbiology
output: note
reset_after: 30
---
{{file:prompts/word-core.md}}

{{file:prompts/word-microbiology.md}}
--- followup ---
New term: {term}
Under heading: {heading}
Same lesson, same rules and same template as before. Reply in exactly the same output format (destination line first, then the frontmatter).
