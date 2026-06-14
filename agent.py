"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Usage:
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent("vintage graphic tee under $30, size M",
                       wardrobe=get_example_wardrobe())
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize and return a fresh session dict for one user interaction."""
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── query parsing ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Pull a description, optional size, and optional max_price out of the raw
    query using simple regex. Returns a dict with those three keys.
    """
    q = query.strip()

    # max_price: "under $30", "below 30", "$30", "< 40"
    price = None
    price_match = re.search(r"(?:under|below|<|\$)\s*\$?\s*(\d+(?:\.\d+)?)", q, re.I)
    if price_match:
        price = float(price_match.group(1))

    # size: "size M", "size 8", "in size XS"
    size = None
    size_match = re.search(r"size\s+([a-z0-9]+)", q, re.I)
    if size_match:
        size = size_match.group(1)

    # description: strip out the size/price phrases so they don't pollute keywords
    description = re.sub(r"(?:under|below|<|\$)\s*\$?\s*\d+(?:\.\d+)?", "", q, flags=re.I)
    description = re.sub(r"size\s+[a-z0-9]+", "", description, flags=re.I).strip()

    return {"description": description, "size": size, "max_price": price}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the planning loop for a single interaction
    and returns the completed session dict. Check session["error"] first.
    """
    # Step 1: fresh session
    session = _new_session(query, wardrobe)

    # Step 2: parse the query
    session["parsed"] = _parse_query(query)
    parsed = session["parsed"]

    # Step 3: search
    session["search_results"] = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )

    # Branch: no results → set error and stop. Do NOT call suggest_outfit.
    if not session["search_results"]:
        bits = []
        if parsed["size"]:
            bits.append(f"size {parsed['size']}")
        if parsed["max_price"] is not None:
            bits.append(f"under ${parsed['max_price']:.0f}")
        extra = f" ({', '.join(bits)})" if bits else ""
        session["error"] = (
            f"No listings matched your search{extra}. "
            "Try loosening the filters — raise the price, drop the size, "
            "or use broader keywords (e.g. 'jacket' instead of 'vintage band jacket')."
        )
        return session

    # Step 4: select the top result
    session["selected_item"] = session["search_results"][0]

    # Step 5: suggest an outfit using the selected item + wardrobe
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    # Step 6: create the fit card from the outfit + item
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: done
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")