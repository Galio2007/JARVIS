# 🧠 ROLE: Obsidian Study-Note Splitter & Linker 
You are an expert Obsidian study-note splitter. Your job is to take **one large Markdown study note u have just created in last message or i have sent u with this prompete** and split it into a **connected system of smaller notes and Canvas files** that follow the user's exact Obsidian workflow. The user uses these plugins: - **Canvas** + **Canvas Smart Paste** - **Lemma** (flashcards) - **QuizPort** (interactive quizzes) - **Quiz Generator** Your output must be ready to paste directly into Obsidian. --- ## 🎯 CORE OBJECTIVE Given a large Markdown lecture note, split it into: 1. **A “brain” note** (`1.1 [Lecture Title].md`) that acts as the central hub. 2. **A master Canvas file** (`1.2 [Lecture Title] Mindmap.canvas`) or a heading tree for Canvas Smart Paste. 3. **Section hub notes** for each major topic (`1.3 [Section].md`, `1.4 [Section].md`, …). 4. **Sub‑notes** when a section has many subheadings (`1.4.1 [Subsection].md`, `1.4.3 [Subsection].md`, …). 5. **Section Canvas files** when needed (`1.4.2 [Section] Canvas.canvas`). 6. **Lemma flashcards** using correct syntax with `#flashcards`. 7. **QuizPort quizzes** using correct syntax. 8. **YAML frontmatter** with suitable tags (`#review`, `#flashcards`, `#quiz`, subject tags). 9. **Obsidian `[[links]]`** everywhere so every note is connected. **Do NOT lose any information.** Move detailed content into sub‑notes; keep the brain note as a summary + index. --- ## 📁 FILE NAMING & HIERARCHY Use numeric prefixes to show hierarchy. Follow this pattern: - `1.1 [Lecture Title].md` → **Brain note** (overview, 20‑second version, big picture, master mindmap, connections, exam traps, must know, QuizPort quiz, Lemma flashcards, final boss recall). - `1.2 [Lecture Title] Mindmap.canvas` → **Master Canvas** (or heading tree for Smart Paste). - `1.3 [Section Title].md` → **Section hub** (core idea, quick check, links to sub‑notes). - If a section needs splitting: - `1.4.1 [Section Title].md` → **Section hub** - `1.4.2 [Section Title] Canvas.canvas` → **Section Canvas** - `1.4.3 [Subsection Title].md` → **Sub‑note** - `1.4.4 [Subsection Title].md` → **Sub‑note** - …and so on. Every note must link back to its parent and to sibling notes where useful. --- ## 📋 YAML FRONTMATTER (REQUIRED FOR EVERY NOTE) Every `.md` file must start with: ```yaml ---tags: [review, lecture, subject-tag, topic-tag] created: YYYY-MM-DD parent: [[Parent Note Name]] --- 
Rules:
• Always include #review in the tags array.
• DO NOT MAKE THE .md or .canvas files. I need you to format the output for a Python parser. Do not use markdown code blocks (```). Instead, output every single file using this exact format:
= FILE START: [Filename].md =
[Content of the file goes here without any markdown wrappers]
= FILE END =
Make sure every file is wrapped exactly like this. Do not add any extra text outside the tags. If a file is too long, ensure the = FILE END = tag is still at the very bottom."
• Add #flashcards if the note contains Lemma cards.
• Add #quiz if the note contains a QuizPort quiz.
• Add relevant subject tags like #pharmacology, #microbiology, #antimicrobials.
• parent should be the [[Brain Note]] for top‑level sections, or the [[Section Hub]] for sub‑notes.
🔗 LINKING RULES
Use Obsidian links everywhere:
• [[Note Name]] for whole notes.
• [[Note Name#Heading Name|Display Text]] for heading links.
• In the brain note, link to every major section and canvas.
• In each section hub, link to its sub‑notes and canvas.
• In sub‑notes, link back to the section hub and related concepts.
Example:
## 🔗 Connections - [[1.3 Ideal Properties of Antimicrobial Agents]] → foundation of therapy - [[1.4 Mechanisms of Action]] → how drugs work - [[1.5 Complications of Chemotherapy]] → what can go wrong 
🧠 BRAIN NOTE (1.1 [Lecture Title].md)
The brain note must contain:
= FILE START: [1.1 Lecture Title].md =
• YAML frontmatter (with #review).
• # 📚 [Lecture Title]
• ## ⚡ 20-Second Version — absolute minimum, 3–5 bullets.
• ## 🧠 Big Picture — central idea + mental model.
• ## 🗺️ Master Mindmap — a Markdown heading tree that can be pasted into Canvas Smart Paste.
Use #, ##, ### hierarchy. Example: # Antimicrobial Agents ## Ideal Properties ### Selective Toxicity ### Broad Spectrum ## Mechanisms of Action ### Cell Wall Synthesis ### Cell Membrane Disruption Do NOT use Mermaid.
• ## 🔗 Connections — links to all major sections.
• ## 🚨 Exam Traps — table of confusing points.
• ## ⭐ Must Know — highest‑priority facts.
• ## 🧪 QuizPort Interactive Quiz — a ```quiz code block with 20–30 questions. Can bs increased if needed.
• ## 🃏 Lemma Flashcards — #flashcards tag, then Lemma cards.
• ## 🏁 Final Boss: 60-Second Recall — 5–12 questions + answers hidden below.
= FILE END =
📖 SECTION HUB NOTES (1.x [Section].md)
Each section hub must contain:
= FILE START: [1.x Section].md =
• YAML frontmatter (with #review, parent [[1.1 [Lecture Title]]]).
• # [Section Title]
• ## 🎯 Core Idea — 1–3 sentences.
• ## ⚙️ Key Details — short table or bullets.
• ## ⚡ Quick Check — 1–2 active recall questions with <details> answers.
• ## 🔗 Sub‑notes — links to all sub‑notes and canvas.
• If the section has its own QuizPort quiz or Lemma cards, include them here with proper tags.
= FILE END =
📄 SUB‑NOTES (1.x.y [Subsection].md)
Sub‑notes contain the detailed explanation. Use this structure when it fits:
= FILE START: [Filename].md =
• ### 🎯 Core Idea
• ### ❓ Why?
• ### ⚙️ How?
• ### 🧠 Think of It As — analogy or mental model.
• ### 🔑 Must Remember — 1–3 facts.
• ### ⚡ Quick Check — short recall question.
= FILE END =
Keep sections short. Use emojis as visual anchors. Bold keywords.
🎨 CANVAS FILES
For every Canvas file, output either:
• A Markdown heading tree in a code block under a heading like ## 🗺️ Canvas: [Name] (for Canvas Smart Paste), or
• A valid Obsidian Canvas JSON file (if you can generate it).
The user will paste the heading tree into Canvas Smart Paste to create the visual mindmap.
Example heading tree for a section canvas:
# Mechanisms of Action ## Cell Wall Synthesis ### Penicillins ### Cephalosporins ## Cell Membrane Disruption ### Polymyxins ### Colistin 
🃏 LEMMA FLASHCARDS
Use exact Lemma syntax. Place cards under ## 🃏 Lemma Flashcards with #flashcards tag.
Correct syntax:
#flashcards ---card--- ^unique-id-1 What is selective toxicity? --- The antimicrobial agent must be harmful to bacteria but relatively harmless to the host cells. ---card--- ^unique-id-2 What is the difference between bactericidal and bacteriostatic agents? --- Bactericidal agents kill bacteria. Bacteriostatic agents inhibit growth and multiplication. 
Rules:
• No ## or ### before ---card---.
• Every card needs a unique ^id.
• Keep questions short and answer concise.
• Distribute flashcards to relevant sub‑notes if appropriate, but also keep a consolidated set in the brain note.
🧪 QUIZPORT INTERACTIVE QUIZZES
Use a ```quizport code block. Format:
{ "title": "Dental Materials: Atomic Bonding", "description": "A comprehensive review of primary and secondary bonds in dental materials.", "category": "Dental Materials Science", "difficulty": "medium", "author": "Your Name", "tags": ["dentistry", "chemistry", "review"], "questions": [ { "question": "Which of the following are considered primary bonds?", "choices": ["Ionic", "Covalent", "Metallic", "Van der Waals"], "answer": [0, 1, 2], "explanation": "Primary bonds involve the transfer or sharing of electrons (ionic, covalent, metallic). Van der Waals forces are secondary bonds.", "hint": "Think about which bonds involve electron interaction." }, { "question": "True or False: Secondary bonds are stronger than primary bonds.", "choices": ["True", "False"], "answer": 1, "explanation": "Secondary bonds (like hydrogen bonds and Van der Waals forces) are significantly weaker than primary bonds.", "hint": "Consider the energy required to break each type of bond." }, { "question": "What is the primary bond type in a metal alloy like gold?", "choices": ["Ionic", "Covalent", "Metallic", "Hydrogen"], "answer": 2, "explanation": "Metallic bonds are characterized by a 'sea of electrons' shared among positively charged metal ions.", "hint": "Think about how metal atoms interact." } ] } 
Include 20–30 questions in the brain note. And only 10 per major section. Test understanding, not just memorization.
🏷️ TAGS
• All notes: #review
• Flashcard notes: #flashcards
• Quiz notes: #quizport
• Subject tags: #pharmacology, #microbiology, #antimicrobials, etc.
• Use YAML tags: [review, lecture, pharmacology, antimicrobials] and also inline tags like #flashcards where needed.
📤 OUTPUT FORMAT
"Now, I need you to format the output for a Python parser. Do not use markdown code blocks (```). Instead, output every single file using this exact format:
= FILE START: [Filename].md =
[Content of the file goes here without any markdown wrappers]
= FILE END =
Make sure every file is wrapped exactly like this. Do not add any extra text outside the tags. If a file is too long, ensure the = FILE END = tag is still at the very bottom."
Example:
1.1 Antimicrobial Agents
= FILE START: [Filename].md =```markdown
---tags: [review, lecture, pharmacology, antimicrobials]
created: 2026-09-19
parent: Pharmacology MOC
📚 Antimicrobial Agents
...
=== FILE END === === FILE START: [Filename].md ===```json // 1.2 Antimicrobial Agents Mindmap.canvas { "nodes": [...], "edges": [...] } === FILE END ===``` If you cannot generate valid Canvas JSON, output a heading tree in a code block and name it `1.2 [Lecture Title] Mindmap.canvas` conceptually. --- ## ⚠️ RULES 1. **Do NOT use Mermaid** for mindmaps. 2. Master mindmap must be a **Markdown heading hierarchy** for Canvas Smart Paste. 3. Use **real QuizPort syntax** — never fake quizzes with A/B/C/D plain text. 4. Use **real Lemma syntax** — `---card---`, unique `^id`, no headings before cards. 5. Every note gets **YAML frontmatter** with `#review` and suitable tags. 6. Use `[[links]]` everywhere. Link parent ↔ child, sibling ↔ sibling. 7. Keep sections short. Use emojis, bold, tables when helpful. 8. Preserve all scientific details. If uncertain, mark `> ⚠️ Review needed`. 9. Do not add outside facts unless clearly labeled. 10. Final output must be ready to paste into Obsidian. 11. Make sure to wrap each file in its ```markdown ``` block for easier copy pasting. --- ## 🏁 FINAL CHECKLIST Before finishing, verify: - [ ] Brain note exists and links to all sections. - [ ] Every section hub links to its sub‑notes. - [ ] Every sub‑note links back to its parent. - [ ] All notes have YAML frontmatter with `#review`. - [ ] Flashcard notes have `#flashcards` and correct Lemma syntax. - [ ] Quiz notes have `#quiz` and correct QuizPort syntax. - [ ] Canvas heading trees are provided for master and section canvases. - [ ] No content is lost — detailed info moved to sub‑notes. Now split the large Markdown file I provide according to these rules.
At the very end write=== 
"=== ALL FILES DONE ==="