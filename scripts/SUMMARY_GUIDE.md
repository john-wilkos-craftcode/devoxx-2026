# How to summarise a Devoxx Belgium 2026 talk

Input per talk:
- Metadata: `python3 scripts/talk_info.py <id>` prints title, speakers, type, track, abstract.
- Transcript: `data/raw/transcripts/<id>.txt` (YouTube auto-captions, `[mm:ss]` marker about every minute).
  Absent for talks that were not recorded or not yet uploaded: summarise from the abstract instead.

Output: `data/summaries/<id>.json`, then run `python3 scripts/validate_summaries.py <id> ...`.

## Ground rules

- Summarise what was actually **said** in the transcript, not what the abstract promised. Where they
  differ (talk changed direction, demo failed, extra announcement), go with the transcript.
- Auto-captions garble names: speaker names, products, projects ("Devox" = Devoxx, "Gibster" = JHipster,
  "Quarkis" = Quarkus, "Lang chain for J" = LangChain4j, "Jacarta" = Jakarta EE...). Always use the
  correct spelling, using the metadata's speaker names and your own knowledge.
- Be concrete. Name the tools, numbers, APIs, JEPs, patterns and examples the speaker used. "The speaker
  discussed best practices" is worthless; "Run the agent in a container with no network and a
  read-only mount of the repo" is useful.
- Neutral, precise, readable English. No hype words ("game-changing", "revolutionary", "deep dive into").
  Refer to speakers by surname or full name, using they/them unless the talk makes pronouns clear.
- Do not invent. If the transcript is poor or truncated, say less rather than guessing.
- Quotes: lightly cleaned (drop "uh", fix caption errors) but faithful to the words used. Only memorable
  lines, max 3, zero is fine. Timestamp = the `[mm:ss]` marker before the quote.

## JSON schema

```json
{
  "id": 24228,
  "source": "transcript",            // or "abstract"
  "tldr": "One sentence, max 30 words: what the talk argues or shows.",
  "summary": ["2-4 paragraphs of 50-110 words each, telling the story of the talk in order."],
  "keyPoints": ["4-8 bullets, each one specific claim, technique or fact from the talk"],
  "takeaways": ["2-5 things a developer could act on Monday morning, imperative voice"],
  "quotes": [{"text": "verbatim-ish quote", "at": "12:34"}],
  "chapters": [{"at": "00:00", "title": "Short chapter title"}],
  "tech": ["Named technologies, libraries, specs, JEPs, products mentioned substantively"],
  "watchIf": "One sentence: who should watch this and why (e.g. 'You run Spring Boot on Kubernetes and pay for idle memory.').",
  "themes": ["1-3 values from the list below"],
  "demo": true                       // true if a substantial part was live coding / live demo
}
```

- `chapters`: 4-10 entries for transcript talks, first at "00:00", timestamps from the markers, titles
  of 2-6 words in sentence case. For abstract-only talks: `[]`. Same for `quotes`: `[]` without transcript.
- Abstract-only talks: `summary` 1-2 paragraphs, `keyPoints` 3-5, `takeaways` 1-3, `demo` false,
  and phrase as intent ("The session sets out to...", "Attendees build...").
- Short sessions (lunch talks, 15-30 min) get proportionally shorter output: 1-2 paragraphs, 3-5 key points.

## Themes (pick 1-3, exact strings)

- `AI agents & agentic coding`
- `LLMs in Java apps`
- `Java language & JDK`
- `JVM performance & runtime`
- `Spring & frameworks`
- `Architecture & design`
- `Legacy modernization`
- `Testing & quality`
- `Security & supply chain`
- `Cloud native & Kubernetes`
- `Data & databases`
- `Developer experience & tooling`
- `Teams, careers & leadership`
- `Sustainability`
- `Hardware, robots & fun`
- `Frontend & UI`
