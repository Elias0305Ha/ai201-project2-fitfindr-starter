"""
app.py

Gradio interface for FitFindr. Layout is pre-built; handle_query() is filled in
to call run_agent() and map the session results to the three output panels.

Run with:
    python app.py
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    """Called by Gradio on submit. Returns (listing_text, outfit, fit_card)."""
    # 1. Guard against an empty query.
    if not user_query or not user_query.strip():
        return "Please type what you're looking for first.", "", ""

    # 2. Pick the wardrobe.
    if wardrobe_choice == "Empty wardrobe (new user)":
        wardrobe = get_empty_wardrobe()
    else:
        wardrobe = get_example_wardrobe()

    # 3. Run the agent.
    session = run_agent(user_query, wardrobe)

    # 4. Error path → message in first panel, blanks in the others.
    if session["error"]:
        return session["error"], "", ""

    # 5. Success → format the listing nicely.
    item = session["selected_item"]
    listing_text = (
        f"{item['title']}\n"
        f"${item['price']:.2f} · {item['platform']} · {item['condition']} condition\n"
        f"Size: {item['size']}\n"
        f"Style: {', '.join(item['style_tags'])}\n\n"
        f"{item['description']}"
    )

    return listing_text, session["outfit_suggestion"], session["fit_card"]


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(label="🛍️ Top listing found", lines=8, interactive=False)
            outfit_output = gr.Textbox(label="👗 Outfit idea", lines=8, interactive=False)
            fitcard_output = gr.Textbox(label="✨ Your fit card", lines=8, interactive=False)

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()