import os
import gradio as gr

REPO_ID = "AbteeXAILab/lumynax-multimodal-aria-25b-moe"
UPSTREAM = "rhymes-ai/Aria"
TITLE = "LumynaX Multimodal Aria 25B/3.5B MoE"

THEME_CSS = """
:root { --lx-paper:#fffefa; --lx-ink:#0a0a0b; --lx-amber:#e08a2c; }
body, .gradio-container { background: var(--lx-paper) !important; color: var(--lx-ink) !important; }
h1, h2, h3 { font-family: 'Cormorant Garamond', 'EB Garamond', Georgia, serif; }
"""

def chat_stub(message, history):
    return (
        f"This Space is a scaffold for **{TITLE}**. The upstream model is `{UPSTREAM}` "
        f"and the LumynaX package repo is `{REPO_ID}`. Cloud inference for >100B MoE models "
        f"is not run inside this free Space — clone the repo and run `quickstart.py` on a "
        f"capable host. You asked: {message!r}."
    )

with gr.Blocks(css=THEME_CSS, title=TITLE) as demo:
    gr.Markdown(f"# {TITLE}\n*Sovereign intelligence, held in the light.*\n\nLumynaX release scaffold — clone `{REPO_ID}` for the full package.")
    gr.ChatInterface(chat_stub, examples=["Explain LumynaX in 2 bullets.", "Why local-first AI for Aotearoa?"])

if __name__ == "__main__":
    demo.launch()
