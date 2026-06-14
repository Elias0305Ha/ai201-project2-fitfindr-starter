# FitFindr — planning.md

> Written before implementation. Used to direct AI code generation.

---

## Tools

### Tool 1: search_listings

**What it does:**
Searches the mock secondhand listings dataset and returns items that match the
user's keywords, optionally filtered by size and a max price, ranked by how
relevant they are.

**Input parameters:**
- `description` (str): keywords for what the user wants, e.g. "vintage graphic tee".
- `size` (str | None): size to filter by (e.g. "M"); None skips the size filter. Case-insensitive, loose match.
- `max_price` (float | None): price ceiling, inclusive; None skips the price filter.

**What it returns:**
A `list[dict]` of matching listings sorted best-match-first. Each dict has:
id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand, platform.

**What happens if it fails or returns nothing:**
Returns an empty list `[]` (never raises). The agent detects the empty list and
tells the user what to loosen (price, size, or keywords).

---

### Tool 2: suggest_outfit

**What it does:**
Takes a found item plus the user's wardrobe and asks the LLM to suggest 1–2
complete outfits using pieces the user already owns.

**Input parameters:**
- `new_item` (dict): the listing the user is considering buying.
- `wardrobe` (dict): a wardrobe dict with an `items` key holding a list of owned-item dicts. May be empty.

**What it returns:**
A non-empty `str` with outfit suggestions.

**What happens if it fails or returns nothing:**
If `wardrobe["items"]` is empty, it asks the LLM for general styling advice for
the item instead of crashing — still returns a useful string.

---

### Tool 3: create_fit_card

**What it does:**
Turns an outfit suggestion into a short, shareable Instagram/TikTok-style caption.

**Input parameters:**
- `outfit` (str): the outfit suggestion text from suggest_outfit().
- `new_item` (dict): the listing dict, used for name/price/platform.

**What it returns:**
A 2–4 sentence caption `str`. Uses a high LLM temperature so it varies per input.

**What happens if it fails or returns nothing:**
If `outfit` is empty or whitespace-only, it returns a descriptive error message
string (no exception).

---

## Planning Loop

The agent runs one query through an ordered loop that branches on results:

1. Parse the query into `description`, `size`, `max_price` (regex).
2. Call `search_listings`. **If results is empty → set `session["error"]` and return early. Do NOT call the other tools.**
3. If results exist → `selected_item = results[0]`.
4. Call `suggest_outfit(selected_item, wardrobe)` → store `outfit_suggestion`.
5. Call `create_fit_card(outfit_suggestion, selected_item)` → store `fit_card`.
6. Return the session.

The behavior changes based on what search returns: empty → error branch and stop;
non-empty → continue through outfit + card. The agent never calls all three tools
unconditionally.

---

## State Management

A single `session` dict is the source of truth for one interaction. It holds the
query, parsed params, search_results, selected_item, wardrobe, outfit_suggestion,
fit_card, and error. Each tool reads what it needs from the session and writes its
result back, so output from one tool flows into the next (e.g. `selected_item`
goes straight into `suggest_outfit`; its return goes into `create_fit_card`)
without the user re-entering anything.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Returns `[]`; agent sets an error telling the user to raise price, drop size, or broaden keywords, and stops. |
| suggest_outfit | Wardrobe is empty | Returns general LLM styling advice for the item instead of crashing. |
| create_fit_card | Outfit input missing/incomplete | Returns a descriptive error string explaining no outfit was provided. |

---

## Architecture

```
User query
    │
    ▼
Planning Loop ───────────────────────────────────────────┐
    │ parse query → description, size, max_price          │
    ├─► search_listings(description, size, max_price)      │
    │       │ results=[]                                   │
    │       ├──► [ERROR] "No listings found..." → return ──┤
    │       │ results=[item, ...]                          │
    │       ▼                                              │
    │   Session: selected_item = results[0]                │
    │       │                                              │
    ├─► suggest_outfit(selected_item, wardrobe)            │
    │       │                                              │
    │   Session: outfit_suggestion = "..."                 │
    │       │                                              │
    └─► create_fit_card(outfit_suggestion, selected_item)  │
            │                                              │
        Session: fit_card = "..."                          │
            │                              error path returns here
            ▼
        Return session
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
I gave Claude each tool's spec block from this file (inputs, return value, failure
mode) one at a time and asked it to implement the function in tools.py using
`load_listings()` from the data loader and Groq's llama-3.3-70b-versatile for the
LLM tools. Before trusting each, I checked it filtered/handled the failure mode I
described, then ran the pytest tests in `tests/`.

**Milestone 4 — Planning loop and state management:**
I gave Claude the agent diagram plus the Planning Loop and State Management
sections and asked it to implement `run_agent()` in agent.py. I verified it
branches on the empty search result (returns early, never calls suggest_outfit)
and that it stores each result in the session dict rather than re-prompting.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers."

**Step 1:** Parse → description "vintage graphic tee", size None, max_price 30.0.
Call `search_listings("vintage graphic tee", None, 30.0)` → returns matching tees
sorted by relevance.

**Step 2:** Results aren't empty, so `selected_item = results[0]` (e.g. a faded
band tee, $22). Call `suggest_outfit(selected_item, wardrobe)` → returns a styling
suggestion using the user's owned baggy jeans and chunky sneakers.

**Step 3:** Call `create_fit_card(outfit_suggestion, selected_item)` → returns a
casual caption mentioning the tee, $22, and the platform.

**Final output to user:** the top listing details, the outfit idea, and the
shareable fit card — shown in the three panels of the app.