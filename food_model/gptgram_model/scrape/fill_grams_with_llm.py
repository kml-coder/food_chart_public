import argparse
import concurrent.futures
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


def extract_float(text):
    match = re.search(r"-?\d+(\.\d+)?", str(text or ""))
    return float(match.group()) if match else None


def call_openai(api_url, api_key, model, unit, size, name, timeout_sec, api_mode, temperature):
    system_prompt = (
        "You estimate ingredient weight in grams.\n"
        "Given unit, size, and ingredient name, estimate grams for ONE unit amount.\n"
        "If unit is empty, estimate grams for one typical item matching size/name.\n"
        "Return ONLY JSON: {\"gram\": <number>} with no extra text."
    )
    user_prompt = (
        f"unit: {unit}\n"
        f"size: {size}\n"
        f"name: {name}\n"
        "Output strict JSON only."
    )

    if api_mode == "responses":
        endpoint = "/v1/responses"
        payload = {
            "model": model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
    else:
        endpoint = "/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
    if temperature is not None:
        payload["temperature"] = temperature
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url.rstrip("/") + endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout_sec) as response:
        data = json.loads(response.read().decode("utf-8"))
        if api_mode == "responses":
            text = data.get("output_text", "")
            if not text:
                # Fallback for payloads without output_text helper field
                parts = []
                for out in data.get("output", []):
                    for c in out.get("content", []):
                        if c.get("type") == "output_text" and c.get("text"):
                            parts.append(c["text"])
                text = "\n".join(parts)
        else:
            text = data["choices"][0]["message"]["content"]

    try:
        parsed = json.loads(text)
        gram = parsed.get("gram")
        return float(gram) if gram is not None else None
    except Exception:
        return extract_float(text)


def main():
    parser = argparse.ArgumentParser(description="Fill output.json gram fields with LLM API")
    parser.add_argument("--input", default="output.json", help="Input json path")
    parser.add_argument("--output", default="output_filled.json", help="Output json path")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model name")
    parser.add_argument(
        "--api-mode",
        default="responses",
        choices=["responses", "chat"],
        help="OpenAI API mode: responses (recommended) or chat completions",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional temperature. Leave unset for models that do not support it.",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("LLM_API_URL", "https://api.openai.com"),
        help="OpenAI-compatible API base URL",
    )
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"), help="API key")
    parser.add_argument("--limit", type=int, default=0, help="Process at most N empty grams (0=all)")
    parser.add_argument("--save-every", type=int, default=50, help="Save every N updates")
    parser.add_argument("--sleep", type=float, default=0.1, help="Sleep seconds between requests")
    parser.add_argument("--timeout-sec", type=int, default=60, help="API timeout per request")
    parser.add_argument("--start-index", type=int, default=0, help="Start index for resume")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of parallel API requests")
    args = parser.parse_args()

    if not args.api_key:
        raise ValueError("Missing API key. Set OPENAI_API_KEY or pass --api-key.")

    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    total_updated = 0
    checked = 0
    candidates = []

    for i in range(args.start_index, len(data)):
        item = data[i]
        gram_value = str(item.get("gram", "")).strip()
        if gram_value:
            continue

        unit = str(item.get("unit", "") or "").strip()
        size = str(item.get("size", "") or "").strip()
        name = str(item.get("name", "") or "").strip()
        if not name:
            continue

        checked += 1
        if args.limit > 0 and checked > args.limit:
            break
        candidates.append((i, unit, size, name))

    def worker(index, unit, size, name):
        try:
            gram = call_openai(
                api_url=args.api_url,
                api_key=args.api_key,
                model=args.model,
                unit=unit,
                size=size,
                name=name,
                timeout_sec=args.timeout_sec,
                api_mode=args.api_mode,
                temperature=args.temperature,
            )
            return index, unit, size, name, gram, None
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = ""
            return index, unit, size, name, None, f"HTTPError: {e.code} {e.reason} | {err_body}"
        except Exception as e:
            return index, unit, size, name, None, f"Error: {e}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = []
        for idx, unit, size, name in candidates:
            futures.append(executor.submit(worker, idx, unit, size, name))
            if args.sleep > 0:
                time.sleep(args.sleep)

        for future in concurrent.futures.as_completed(futures):
            i, unit, size, name, gram, err = future.result()
            if err:
                print(f"[{i}] {err}")
                continue

            if gram is None or gram <= 0:
                print(f"[{i}] no valid gram -> unit={unit} size={size} name={name}")
                continue

            data[i]["gram"] = round(float(gram), 2)
            total_updated += 1
            print(f"[{i}] gram={data[i]['gram']} | {unit} {size} {name}".strip())

            if total_updated % args.save_every == 0:
                with output_path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"Saved progress: {total_updated} updated")

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Done. Updated={total_updated}, output={output_path}")


if __name__ == "__main__":
    main()
