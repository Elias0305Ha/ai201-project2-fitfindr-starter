"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  -> list[dict]
    suggest_outfit(new_item, wardrobe)             -> str
    create_fit_card(outfit, new_item)              -> str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

# Tiny, common words we don't want to count as meaningful keyword matches.
_STOPWORDS = {
    "a", "an", "the", "for", "of", "in", "on", "with", "and", "or", "to",
    "i", "im", "looking", "want", "need", "find", "me", "my", "some",
    "under", "below", "size", "vintage",  # 'vintage' kept out of scoring noise
}


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _llm(prompt: str, temperature: float = 0.6) -> str:
    """Send a single prompt to Groq and return the text reply."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def _size_matches(requested: str, listing_size: str) -> bool:
    """Loose, case-insensitive size match. 'M' matches 'S/M', 'M', etc."""
    if not listing_size:
        return False
    tokens = re.split(r"[\s/,\-]+", listing_size.lower())
    return requested.lower() in tokens


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Returns a list of matching listing dicts sorted by relevance (best first).
    Returns an empty list if nothing matches — does NOT raise.
    """
    listings = load_listings()

    # Build the set of meaningful keywords from the description.
    words = re.findall(r"[a-z0-9]+", description.lower())
    keywords = [w for w in words if w not in _STOPWORDS and len(w) > 1]

    scored = []
    for item in listings:
        # 1. Price filter
        if max_price is not None and item["price"] > max_price:
            continue

        # 2. Size filter
        if size is not None and not _size_matches(size, item.get("size", "")):
            continue

        # 3. Score by keyword overlap across the searchable text fields.
        haystack = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("category", ""),
            " ".join(item.get("style_tags", [])),
            " ".join(item.get("colors", [])),
            item.get("brand") or "",
        ]).lower()

        score = sum(1 for kw in keywords if kw in haystack)

        # 4. Drop anything with no keyword relevance.
        if score > 0:
            scored.append((score, item))

    # 5. Sort by score, highest first.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
    Handles an empty wardrobe by giving general styling advice instead.
    """
    item_desc = (
        f"{new_item.get('title', 'an item')} "
        f"(category: {new_item.get('category', 'unknown')}, "
        f"colors: {', '.join(new_item.get('colors', []))}, "
        f"style: {', '.join(new_item.get('style_tags', []))})"
    )

    items = wardrobe.get("items", [])

    if not items:
        # Empty wardrobe → general styling advice, no crash.
        prompt = (
            f"A user is considering thrifting this item: {item_desc}. "
            "They haven't told us what else they own. In 2-3 sentences, give "
            "warm, specific styling advice: what kinds of pieces pair well with "
            "it, what vibe it suits, and how to wear it. Be encouraging and "
            "concrete, not generic."
        )
        return _llm(prompt, temperature=0.6)

    # Non-empty wardrobe → suggest specific combos using owned pieces.
    wardrobe_lines = "\n".join(
        f"- {w['name']} ({w.get('category', '')}, "
        f"{', '.join(w.get('colors', []))}, "
        f"{', '.join(w.get('style_tags', []))})"
        for w in items
    )
    prompt = (
        f"A user is considering thrifting this item: {item_desc}.\n\n"
        f"Here is what they already own:\n{wardrobe_lines}\n\n"
        "Suggest 1-2 complete outfit combinations that pair the new item with "
        "SPECIFIC pieces from their wardrobe (name them). Keep it to 2-4 "
        "sentences, casual and practical. Mention a small styling tip if it fits."
    )
    return _llm(prompt, temperature=0.6)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    Guards against an empty outfit string by returning an error message string.
    """
    # 1. Guard against missing / whitespace-only outfit.
    if not outfit or not outfit.strip():
        return (
            "Couldn't make a fit card — no outfit was provided. "
            "Try suggesting an outfit first, then generate the caption."
        )

    # 2. Build the caption prompt.
    prompt = (
        "Write a short, shareable Instagram/TikTok caption (2-4 sentences) for "
        "this thrifted outfit. Make it sound like a real OOTD post — casual, a "
        "little excited, NOT a product description.\n\n"
        f"Item: {new_item.get('title', 'a thrifted find')}\n"
        f"Price: ${new_item.get('price', '?')}\n"
        f"Platform: {new_item.get('platform', 'a resale app')}\n"
        f"Outfit idea: {outfit}\n\n"
        "Mention the item, price, and platform naturally (once each). Capture "
        "the specific vibe. You can use 1-2 emojis. No hashtag walls."
    )

    # 3. Higher temperature so it varies for different inputs.
    return _llm(prompt, temperature=0.95)