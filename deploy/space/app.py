"""Hugging Face Space entrypoint (Gradio SDK, ZeroGPU hardware).

One ASGI app serves three things on port 7860:

    /gradio/  a Gradio demo of the gram estimator
    /api/*    the existing Flask app from food_server/server.py, unmodified
    /*        the exported Expo web bundle

The Flask app is mounted as WSGI rather than rewritten, so the same server.py
runs here and in the Docker image.
"""
import os

# `spaces` MUST be imported before anything that initializes CUDA — it raises
# RuntimeError otherwise, and `import server` pulls in torch. So this import
# comes first, before every other project import.
#
# ImportError is the normal local case (the package only exists on Space
# infrastructure). Any other failure is caught too, so a broken GPU path
# degrades to CPU inference instead of taking the whole app down.
try:
    import spaces

    SPACES_AVAILABLE = True
except Exception as exc:  # noqa: BLE001
    print(f"[app] spaces unavailable ({exc.__class__.__name__}: {exc}); using CPU")
    SPACES_AVAILABLE = False

# Must be set before importing server: it loads the model at import time.
os.environ.setdefault("DEBERTA_MODEL_PATH", "KL946/deberta-v3-base-grams")
os.environ.setdefault("USE_OLLAMA_GRAMS", "false")
# The FastAPI layer serves the web bundle, so Flask must not also claim "/".
os.environ["STATIC_DIR"] = ""

import gradio as gr
from a2wsgi import WSGIMiddleware
from fastapi.responses import FileResponse, JSONResponse

import server

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")

# ----------------------------------------------------------------------
# ZeroGPU: one allocation per request, not per ingredient.
#
# Outside an @spaces.GPU function ZeroGPU runs a CUDA emulation layer, so
# server.py's `.to(device)` at import time already puts the model on cuda.
# The decorator below is what actually gets a real GPU.
#
# Without `spaces` (local runs, the Docker image), the hook stays unset and
# predictions take server.py's normal per-item CPU path.
# ----------------------------------------------------------------------
if SPACES_AVAILABLE:

    @spaces.GPU(duration=60)
    def _predict_batch(items):
        return {
            index: server.estimate_grams_with_deberta(item, return_trace=True)
            for index, item in enumerate(items)
        }

    server.deberta_batch_runner = _predict_batch


def estimate(line):
    """Single-line gram estimate, for the Gradio demo tab."""
    line = (line or "").strip()
    if not line:
        return None, "Enter an ingredient line."
    try:
        from ingredient_parser import parse_ingredient

        parsed = parse_ingredient(line)
        item = {
            "raw": line,
            "name": parsed.name[0].text if parsed.name else line,
            "unit": str(parsed.amount[0].unit) if parsed.amount else "",
            "quantity": float(parsed.amount[0].quantity) if parsed.amount else 1.0,
        }
    except Exception:
        item = {"raw": line, "name": line, "unit": "", "quantity": 1.0}

    batched = server.run_deberta_batch([item])
    result = batched.get(0) or server.estimate_grams_with_deberta(item, return_trace=True)
    grams = result["predicted_grams"] * (item["quantity"] or 1.0)
    return round(grams, 1), result.get("trace", {}).get("input_text", "")


with gr.Blocks(title="Food Chart — gram estimator") as demo:
    gr.Markdown(
        "# Food Chart — ingredient gram estimator\n"
        "DeBERTa-v3-base fine-tuned to predict the weight in grams of an "
        "ingredient line, including vague units like `a pinch` or `a clove`.\n\n"
        "The full recipe-to-pie-chart app is at [/app](/app)."
    )
    with gr.Row():
        line_in = gr.Textbox(label="Ingredient line", placeholder="3 cloves garlic")
        grams_out = gr.Number(label="Estimated grams")
    normalized = gr.Textbox(label="Normalized model input", interactive=False)
    gr.Examples(
        [["3 cloves garlic"], ["1 pinch of salt"], ["2 cups flour"], ["1 large onion"]],
        inputs=line_in,
    )
    line_in.submit(estimate, line_in, [grams_out, normalized])

def _bundle_file(path):
    """Resolve a path inside the web bundle, or None if it escapes / is absent."""
    root = os.path.abspath(WEB_DIR)
    if not os.path.isdir(root):
        return None
    candidate = os.path.abspath(os.path.join(root, path))
    if candidate != root and not candidate.startswith(root + os.sep):
        return None  # traversal attempt
    if os.path.isfile(candidate):
        return candidate
    # expo-router's static export writes one `<route>.html` per route.
    if os.path.isfile(candidate + ".html"):
        return candidate + ".html"
    return None


def attach_routes(fastapi_app):
    """Add the Flask API and the Expo bundle to Gradio's own FastAPI app.

    Routes are appended, so every Gradio route already registered keeps
    priority. That is why the Expo app lives under /app instead of "/": Gradio
    owns the root path and cannot be displaced.
    """
    fastapi_app.mount("/api", WSGIMiddleware(server.app))

    # expo-router emits absolute asset URLs (/_expo/..., /assets/...), so those
    # prefixes have to resolve at the root even though the app is under /app.
    @fastapi_app.get("/_expo/{path:path}")
    def expo_asset(path: str):
        found = _bundle_file(f"_expo/{path}")
        return FileResponse(found) if found else JSONResponse({"error": "not found"}, 404)

    @fastapi_app.get("/assets/{path:path}")
    def bundle_asset(path: str):
        found = _bundle_file(f"assets/{path}")
        return FileResponse(found) if found else JSONResponse({"error": "not found"}, 404)

    @fastapi_app.get("/app")
    @fastapi_app.get("/app/{path:path}")
    def spa(path: str = ""):
        found = _bundle_file(path) or _bundle_file("index.html")
        return FileResponse(found) if found else JSONResponse({"error": "no bundle"}, 404)


if __name__ == "__main__":
    # HF's Space runtime already owns port 7860, so this must not start its own
    # uvicorn — that was an "address already in use" crash. Gradio's launch()
    # knows how to attach to the Space runtime.
    #
    # Routes have to be added *after* launch: launch() rebuilds demo.app, which
    # silently discards anything mounted beforehand.
    # ssr_mode=False is required, not cosmetic. With SSR on, Gradio puts a Node
    # proxy on 7860 and runs Python on 7861; that proxy only forwards Gradio's
    # own routes and answers everything else with the Gradio page, so /api and
    # /app below would be unreachable. It is also what held 7860 and made an
    # earlier attempt to run our own uvicorn fail with "address already in use".
    #
    # Gradio binds 127.0.0.1 by default, which is unreachable from outside the
    # container. The Space runtime sets GRADIO_SERVER_NAME; fall back to 0.0.0.0.
    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        ssr_mode=False,
        prevent_thread_lock=True,
    )
    attach_routes(demo.app)
    print("[app] API mounted at /api, web bundle at /app", flush=True)
    demo.block_thread()
