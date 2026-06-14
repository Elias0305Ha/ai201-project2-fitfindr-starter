# FitFindr 🛍️

A multi-tool AI agent that helps you find secondhand clothing and figure out how
to wear it. You describe what you want in plain language; the agent searches mock
listings, suggests an outfit using your existing wardrobe, and writes a shareable
caption — handling failures gracefully along the way.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── tools.py                   # The three tools
├── agent.py                   # The planning loop
├── app.py                     # Gradio interface
├── tests/test_tools.py        # pytest tests
├── planning.md                # Design spec
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file in the repo root (get a free key at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Run the app:

```bash
python app.py
```

Then open the localhost URL printed in your terminal.

## Tool Inventory

**search_listings(description: str, size: str | None, max_price: float | None) → list[dict]**
Searches the mock listings dataset. Filters by size and max_price (when given),
scores remaining items by keyword overlap with the description, drops zero-score
items, and returns the matches sorted best-first. Returns `[]` when nothing
matches. Purpose: find candidate items to buy.

**suggest_outfit(new_item: dict, wardrobe: dict) → str**
Asks the LLM (Groq llama-3.3-70b-versatile) to suggest 1–2 outfits pairing the
found item with pieces the user already owns. If the wardrobe is empty, returns
general styling advice instead. Purpose: turn a find into a wearable look.

**create_fit_card(outfit: str, new_item: dict) → str**
Asks the LLM (high temperature, so output varies) for a 2–4 sentence
Instagram/TikTok caption mentioning the item, price, and platform. Returns a
descriptive error string if the outfit is empty. Purpose: make the look
shareable.

## How the Planning Loop Works

`run_agent()` runs one query through an ordered loop that branches on what comes
back. It parses the query into description/size/max_price, then calls
`search_listings`. **If the search returns an empty list, it sets `session["error"]`
and returns immediately — it does not call `suggest_outfit` or `create_fit_card`.**
If there are results, it selects the top one, calls `suggest_outfit` with it and
the wardrobe, then feeds that suggestion into `create_fit_card`. The agent's
behavior is therefore conditional on the search result, not a fixed sequence.

## State Management

A single `session` dict holds everything for one interaction: the query, parsed
params, search_results, selected_item, wardrobe, outfit_suggestion, fit_card, and
error. Each tool's output is written back into the session and read by the next
tool — `selected_item` flows into `suggest_outfit`, whose return flows into
`create_fit_card` — so nothing has to be re-entered between steps.

## Error Handling (per tool)

- **search_listings** — no matches: returns `[]`; the agent reports what to loosen
  (price, size, keywords) and stops. Example: `"designer ballgown size XXS under $5"`
  returns an empty list and the user sees a "try loosening your filters" message.
- **suggest_outfit** — empty wardrobe: returns general styling advice rather than
  crashing. Tested with `get_empty_wardrobe()`.
- **create_fit_card** — empty outfit string: returns a descriptive error message
  string instead of raising. Tested by passing `""` as the outfit.

## Spec Reflection

The spec helped most by forcing the tool interfaces to be decided before coding —
knowing exactly what each function takes and returns made wiring the planning loop
straightforward. Implementation diverged slightly on size matching: the data mixes
formats like `"US 9"` and `"M"`, so instead of an exact match the size filter
tokenizes the listing's size and does a loose, case-insensitive token match.

## AI Usage

1. **Tools:** I gave Claude each tool's spec block from planning.md one at a time
   and asked it to implement the function. For `search_listings` I had it use
   `load_listings()` rather than re-reading the file, and reviewed the keyword
   scoring + zero-score drop, which over-matched on the first draft.
2. **Planning loop:** I gave Claude the agent diagram plus the Planning Loop and
   State Management sections and asked for `run_agent()`. I verified it branches
   on the empty-results case and returns early, and that size/price are parsed
   from natural language rather than passed in separately.