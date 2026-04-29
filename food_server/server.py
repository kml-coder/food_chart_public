from flask import Flask,request,jsonify
from flask_cors import CORS
from recipe_scrapers import scrape_me, WebsiteNotImplementedError
from ingredient_parser import parse_ingredient
from fractions import Fraction
from bs4 import BeautifulSoup
from transformers import (
    T5Tokenizer,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    AutoModelForSequenceClassification,
)
import torch
import os

import requests, json, csv, re, time

app= Flask(__name__)
CORS(app)



# TODO 
    # (Done) 1. change all the data and get ratio in the server, make Chartdata(ratio) and 
    # Exceptdata(special equipment or etc), and title, and raw-ingredients(to check)
    # it was well transcripted
    # 2. if quantity is as needed or something 애매함, then put them in the except data
    # also like special equipment like foil or something, then we except that too
    # 3. percent calculating in jsx also bring here
    # 4. (done)적용되는 사이트가 아니면 mapping 된다고 하면서 오류나는거 대신 지원되지 않는 페이지라고 뜨게 해주기
    # 5. unit은 can으로 잡히는데 1 can (6 ounce) 이런 문장이라 ounce가 안 잡히는 경우를 대비하기 위해 amount에서 읽어주기 
color_list = [
    "#fae054", "#a6db49", "#40b885", "#56b2dc", "#435fa7", "#7c4a9c",
    "#e16c8c", "#fa9a4d", "#f26c2a", "#db3d3d", "#8a888b", "#4d4d4d"
]

unitmap = {

        # Gram based
        'gram': 1,
        'grams': 1,
        'g': 1,

        # Kg base
        'kg': 1000,
        'kilograms': 1000,
        'kilogram': 1000,

        # Ounce-based
        'ounce': 28.35,
        'ounces': 28.35,
        'oz': 28.35,
        'onze': 28.35,  

        # Fluid ounce (1 fl oz ≈ 2 tbsp)
        'fluid ounce': 28.35,
        'fluid ounces': 28.35,
        'fl oz': 28.35,

        # Pound
        'pound': 453.6,
        'lb': 453.6,
        'lbs': 453.6,

        # --부피 단위지만 주로 쓰이는게 액체라 환산 가능한 것들--

        # Pint (1 pt = 32 tbsp)
        'pint': 473,
        'pt': 473,

        # Quart (1 qt = 64 tbsp)
        'quart': 946,
        'qt': 946,

        # Gallon (1 gal = 256 tbsp)
        'gallon': 3785,
        'gal': 3785,

        # Metric (approximate to tbsp) # 이거는 되도록 제외하기
        'milliliter': 1,
        'milliliters': 1,
        'ml': 1,

        'liter': 1000,
        'liters': 1000,
        'l': 1000, # 이거는 조심하기 l가 알파벳 하나라 좀 오류 작동할 수 있을듯

# # Cup
#         'cup': 240,
#         'cups': 16,
#         'c': 16,

#         # Tablespoon (base unit)
#         'tablespoon': 1,
#         'tablespoons': 1,
#         'tbsp': 1,
#         'tbsps': 1,

#         # Teaspoon
#         'teaspoon': 1 / 3,
#         'teaspoons': 1 / 3,
#         'tsp': 1 / 3,
#         'tsps': 1 / 3,

#         # Pint (1 pt = 32 tbsp)
#         'pint': 32,
#         'pt': 32,

#         # Quart (1 qt = 64 tbsp)
#         'quart': 64,
#         'qt': 64,

#         # Gallon (1 gal = 256 tbsp)
#         'gallon': 256,
#         'gal': 256,
    }

MODEL_PATH = "./model"  # path that you downloaded model folder
DEBERTA_MODEL_PATH = os.getenv(
    "DEBERTA_MODEL_PATH",
    "../food_model/gptgram_model/artifacts/deberta_v3_base_grams_text_input_final",
)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")
USE_OLLAMA_GRAMS = os.getenv("USE_OLLAMA_GRAMS", "true").lower() == "true"
# [LOCAL-ONLY MODE]
# No EC2/public backend endpoint is used in server runtime.
tokenizer = None
model = None
model_load_error = None
deberta_tokenizer = None
deberta_model = None
deberta_load_error = None
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

try:
    tokenizer = T5Tokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)
    model = model.to(device)
except Exception as e:
    model_load_error = str(e)

try:
    deberta_tokenizer = AutoTokenizer.from_pretrained(DEBERTA_MODEL_PATH)
    deberta_model = AutoModelForSequenceClassification.from_pretrained(
        DEBERTA_MODEL_PATH
    )
    deberta_model = deberta_model.to(device)
    deberta_model.eval()
except Exception as e:
    deberta_load_error = str(e)


def extract_first_float(text):
    match = re.search(r"-?\d+(\.\d+)?", str(text or ""))
    return float(match.group()) if match else None


def estimate_grams_with_ollama(item, ollama_model=None):
    raw_text = str(item.get("raw", "") or "")
    parsed_name = str(item.get("name", "") or "")
    parsed_unit = str(item.get("unit", "") or "")
    parsed_quantity = item.get("quantity", "")

    system_prompt = (
        "You estimate food ingredient weight in grams.\n"
        "Important: Return total grams for the entire ingredient line.\n"
        "Return ONLY one numeric value. No unit, no explanation."
    )
    user_prompt = (
        f"Ingredient line: {raw_text}\n"
        f"Parsed name: {parsed_name}\n"
        f"Parsed quantity: {parsed_quantity}\n"
        f"Parsed unit: {parsed_unit}\n"
        "Estimate total grams for this full line. Return one number only."
    )

    model_name = ollama_model or OLLAMA_MODEL
    payload = {
        "model": model_name,
        "stream": False,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    content = data.get("message", {}).get("content", "")
    predicted = extract_first_float(content)
    if predicted is None:
        raise ValueError(f"Ollama returned no numeric value: {content!r}")
    return predicted


def estimate_grams_with_local_model(item, return_trace=False):
    if model is None or tokenizer is None:
        raise RuntimeError(model_load_error or "Local T5 model is not loaded")

    raw_text = str(item.get("raw", "") or "")
    parsed_name = str(item.get("name", "") or "")
    parsed_unit = str(item.get("unit", "") or "")
    parsed_quantity = item.get("quantity", "")

    # Keep local model input format close to training-style prompt.
    local_prompt = (
        f"Estimate weight: {parsed_unit} {parsed_quantity} {parsed_name}".strip()
        if (parsed_name or parsed_unit or parsed_quantity)
        else raw_text
    )

    inputs = tokenizer(local_prompt, return_tensors="pt").to(device)
    outputs = model.generate(**inputs, max_length=50)
    pred_str = tokenizer.decode(outputs[0], skip_special_tokens=True)
    predicted = extract_first_float(pred_str)
    if predicted is None:
        raise ValueError(f"Local T5 returned no numeric value: {pred_str!r}")
    if not return_trace:
        return predicted

    return {
        "predicted_grams": predicted,
        "trace": {
            "input_raw": raw_text,
            "input_prompt": local_prompt,
            "generated_text": pred_str,
            "parsed_number": predicted,
            "device": str(device),
            "model_path": MODEL_PATH,
        },
    }


def build_deberta_text_input(item):
    def norm(x):
        return str(x or "").strip().lower()

    def get_a_or_an(word):
        if not word:
            return "a"
        return "an" if word[0].lower() in "aeiou" else "a"

    size = norm(item.get("size", ""))
    unit = norm(item.get("unit", ""))
    name = norm(item.get("name", ""))
    if unit:
        # DeBERTa model input is always normalized to a single-item phrasing.
        article = get_a_or_an(unit)
        prefix = f"{article} {size}".strip()
        return f"{prefix} {unit} of {name}".strip().replace("  ", " ")

    article = get_a_or_an(size if size else name)
    prefix = f"{article} {size}".strip()
    return f"{prefix} {name}".strip().replace("  ", " ")


def estimate_grams_with_deberta(item, return_trace=False):
    if deberta_model is None or deberta_tokenizer is None:
        raise RuntimeError(deberta_load_error or "Local DeBERTa model is not loaded")

    text_input = build_deberta_text_input(item)
    with torch.no_grad():
        inputs = deberta_tokenizer(
            text_input,
            return_tensors="pt",
            truncation=True,
            max_length=96,
        ).to(device)
        logits = deberta_model(**inputs).logits.squeeze(-1)
        pred_log = float(logits.detach().cpu().item())

    # Notebook training uses log1p(label), so invert with expm1.
    predicted = max(0.0, float(torch.expm1(torch.tensor(pred_log)).item()))
    if not return_trace:
        return predicted

    return {
        "predicted_grams": predicted,
        "trace": {
            "input_raw": str(item.get("raw", "") or ""),
            "input_text": text_input,
            "pred_log1p": pred_log,
            "predicted_grams": predicted,
            "device": str(device),
            "model_path": DEBERTA_MODEL_PATH,
        },
    }


def estimate_grams_with_heuristic(item):
    # Final fallback so we avoid returning all zeros.
    try:
        q = float(item.get("quantity", 1) or 1)
    except Exception:
        q = 1.0
    if q <= 0:
        q = 1.0

    unit = str(item.get("unit", "") or "").strip().lower()
    name = str(item.get("name", "") or "").strip().lower()

    # Approximate gram-per-unit for common cooking units.
    gram_per_unit = {
        "cup": 240.0,
        "cups": 240.0,
        "tablespoon": 15.0,
        "tablespoons": 15.0,
        "tbsp": 15.0,
        "teaspoon": 5.0,
        "teaspoons": 5.0,
        "tsp": 5.0,
        "ounce": 28.35,
        "ounces": 28.35,
        "oz": 28.35,
        "pound": 453.6,
        "lb": 453.6,
        "lbs": 453.6,
        "clove": 5.0,
        "cloves": 5.0,
        "slice": 25.0,
        "slices": 25.0,
    }

    if unit in gram_per_unit:
        return max(0.0, q * gram_per_unit[unit])

    # Name-based rough defaults when unit is unknown.
    if "egg" in name:
        return max(0.0, q * 50.0)
    if "onion" in name:
        return max(0.0, q * 110.0)
    if "garlic" in name:
        return max(0.0, q * 5.0)

    # Last-resort default.
    return max(0.0, q * 30.0)

def parse_ingredient_line(line, i):
    parsed = parse_ingredient(line)
    amounts = parsed.amount
    name = parsed.name[0].text if parsed.name else ''
    color = color_list[i % len(color_list)]

    if not amounts:
        return { # except data
            "name": name,
            "value": 0,
            "unit": "",
            "color": color,
            "quantity": "",
            "raw": line
        }

    # ------------------------------------------------------------------
    # [LEGACY LOGIC - kept for reference]
    # amount = None
    # for amt in amounts:
    #     if str(amt.unit).lower() in unitmap:
    #         amount = amt
    #         break
    # if not amount:
    #     amount = amounts[0]
    # ------------------------------------------------------------------

    # New active logic:
    # Try multiple amount candidates and select the first one whose unit
    # exists in unitmap. This helps when the first parsed candidate is vague
    # but later candidates contain directly usable units.
    amount = None
    for amt in amounts:
        unit_candidate = str(getattr(amt, "unit", "") or "").strip().lower()
        if unit_candidate in unitmap:
            amount = amt
            break
    if not amount:
        amount = amounts[0]

    # ------------------------------------------------------------------
    # [SCORING-BASED SELECTION - disabled for now, kept for future use]
    # If you want a smarter selector later (e.g., prefer oz over can when
    # both are present), you can enable this block.
    #
    # def _amount_score(amt):
    #     unit_candidate = str(getattr(amt, "unit", "") or "").strip().lower()
    #     score = 0
    #
    #     # Strong signal: directly convertible unit.
    #     if unit_candidate in unitmap:
    #         score += 100
    #
    #     # Prefer mass-like units when available.
    #     if unit_candidate in {"g", "gram", "grams", "kg", "kilogram",
    #                           "kilograms", "oz", "ounce", "ounces",
    #                           "lb", "lbs", "pound"}:
    #         score += 30
    #
    #     # Light penalty for vague recipe units.
    #     if unit_candidate in {"handful", "pinch", "dash", "to taste"}:
    #         score -= 20
    #
    #     # Slight preference for candidates with a valid numeric quantity.
    #     try:
    #         q = float(getattr(amt, "quantity", 0) or 0)
    #         if q > 0:
    #             score += 5
    #     except Exception:
    #         pass
    #
    #     return score
    #
    # scored = sorted(amounts, key=_amount_score, reverse=True)
    # amount = scored[0] if scored else None
    # ------------------------------------------------------------------

    # quantity
    if amount and isinstance(amount.quantity, Fraction):
        quantity = float(amount.quantity)
    else:
        try:
            quantity = float(amount.quantity) if amount and amount.quantity else 0
        except:
            quantity = 0

    # unit 처리
    if amount and amount.unit:
        unit = str(amount.unit)
    else:
        unit = ''



    unit_key = unit.lower() if isinstance(unit, str) else str(unit).lower()
    try:
        value = quantity * unitmap.get(unit_key, 0) if unit else 0
    except Exception as e:
        value = 0

    # Fallback:
    # If main parsed unit is not directly convertible (e.g., "can"),
    # try to recover gram-convertible info from parsed size/raw text
    # such as "6 oz can tomato paste".
    if value <= 0:
        size_text = ""
        try:
            size_text = str(amount.quantity_max) if getattr(amount, "quantity_max", None) else ""
        except Exception:
            size_text = ""

        raw_text = str(line or "")
        search_text = f"{raw_text} {size_text}".lower()

        # Match "<number> <unit>" patterns in free text.
        # Examples:
        # - 6 oz
        # - 6 ounce
        # - 14.5 ounces
        # - 250 g
        token_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(grams?|g|kilograms?|kg|ounces?|oz|onze|"
            r"fluid\s*ounces?|fl\s*oz|pounds?|lbs?|lb|milliliters?|ml|liters?|l)\b"
        )
        matches = token_pattern.findall(search_text)
        if matches:
            # Use first valid convertible token.
            for num_str, unit_str in matches:
                normalized_unit = re.sub(r"\\s+", " ", unit_str.strip().lower())
                try:
                    num_val = float(num_str)
                except Exception:
                    continue
                if normalized_unit in unitmap:
                    value = num_val * unitmap[normalized_unit]
                    # Keep parsed unit label if available; otherwise expose recovered unit.
                    if not unit:
                        unit = normalized_unit
                    # Quantity in this fallback represents the recovered numeric amount.
                    quantity = num_val
                    break

    return {
        "name": name,
        "value": value,
        "unit": unit,
        "color": color,
        "quantity": quantity,
        "raw": line
    }

# Save query and estimated grams
def save_results_to_json(data, filename="estimated_grams.json"):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
def save_results_to_csv(data, filename="estimated_grams.csv"):
    with open(filename, "w") as f:
        writer = csv.DictWriter(f, fieldnames=["query", "estimated_grams"])
        writer.writeheader()
        writer.writerows(data)
        
    
@app.route('/get-ingredients', methods =['GET'])
def get_ingredients():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required, 400'}), 400
    try:
        scraper = scrape_me(url)
        groups = scraper.ingredient_groups() # get ingredients groups
        groups_data = []
        for group in groups:
            parsed = [parse_ingredient_line(line, i) for i,line in enumerate(group.ingredients)] # enumerate 하면 인덱스 먼저 그리고 값이 나온다
            chart_data = []
            except_data = []

            for item in parsed:
                if item['value'] > 0:
                    chart_data.append(item)
                else:
                    except_data.append(item)

            groups_data.append({
                "purpose": group.purpose,
                "chartData": chart_data,
                "exceptData": except_data,
            })
        return jsonify({
            'title': scraper.title(),
            'groupsData': groups_data,
            'raw_ingredients': scraper.ingredients() # ingredients는 method ingredients()를 해야 return값이 나옴
        })
    except WebsiteNotImplementedError:
        return jsonify({'error': "Not supported recipe Website."}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/parse-text', methods=['POST'])
def parse_text():
    data = request.get_json()
    text = data.get("text",'')
    if not text.strip():
        return jsonify({'error': 'No ingredient lines provided'}), 400
    lines = text.split('\n')
    if not lines:
        return jsonify({'error': 'No ingredient lines provided'}), 400
    parsed = [parse_ingredient_line(line, i) for i, line in enumerate(lines)]
    chart_data = [item for item in parsed if item['value'] > 0]
    except_data = [item for item in parsed if item['value'] == 0]
    groups_data = [{
        "purpose": "",
        "chartData": chart_data,
        "exceptData": except_data
    }]
    return jsonify({
            'title' : "",
            'groupsData': groups_data,
            'raw_ingredients': lines
        })
@app.route('/predict-grams', methods=['POST'])
def predict_grams():
    try:
        data = request.json or {}
        except_data = data.get("exceptData", [])
        request_ollama_model = data.get("ollamaModel")

        results = []
        for item in except_data:
            text = item.get("raw", "")
            quantity = item.get("quantity", 1)  # default 1

            if not text:
                continue

            try:
                quantity_value = float(quantity) if quantity else 1.0
            except:
                quantity_value = 1.0

            base_grams = 0.0
            ollama_error = None
            local_error = None
            fallback_error = None
            t5_trace = None
            deberta_trace = None
            selected_model_name = str(request_ollama_model or OLLAMA_MODEL)
            use_local_t5 = selected_model_name.lower().startswith("t5")
            use_local_deberta = selected_model_name.lower().startswith("deberta")
            model_used = "unknown"

            if use_local_deberta:
                try:
                    deberta_result = estimate_grams_with_deberta(item, return_trace=True)
                    base_grams = deberta_result["predicted_grams"]
                    deberta_trace = deberta_result.get("trace")
                    model_used = "deberta_local"
                except Exception as e:
                    local_error = str(e)
                    try:
                        base_grams = estimate_grams_with_ollama(item, OLLAMA_MODEL)
                        model_used = f"ollama_fallback:{OLLAMA_MODEL}"
                    except Exception as fallback_e:
                        fallback_error = str(fallback_e)
                        try:
                            local_result = estimate_grams_with_local_model(
                                item, return_trace=True
                            )
                            base_grams = local_result["predicted_grams"]
                            t5_trace = local_result.get("trace")
                            model_used = "t5_local_fallback"
                        except Exception as t5_fallback_e:
                            local_error = f"{local_error} | t5_fallback: {t5_fallback_e}"
                            base_grams = estimate_grams_with_heuristic(item)
                            model_used = "heuristic_fallback"
            elif use_local_t5:
                try:
                    local_result = estimate_grams_with_local_model(item, return_trace=True)
                    base_grams = local_result["predicted_grams"]
                    t5_trace = local_result.get("trace")
                    model_used = "t5_local"
                except Exception as e:
                    local_error = str(e)
                    # If T5 is unavailable in Docker, fallback to Ollama default model.
                    try:
                        base_grams = estimate_grams_with_ollama(item, OLLAMA_MODEL)
                        model_used = f"ollama_fallback:{OLLAMA_MODEL}"
                    except Exception as fallback_e:
                        fallback_error = str(fallback_e)
                        base_grams = estimate_grams_with_heuristic(item)
                        model_used = "heuristic_fallback"
            else:
                if USE_OLLAMA_GRAMS:
                    try:
                        base_grams = estimate_grams_with_ollama(item, request_ollama_model)
                        model_used = f"ollama:{request_ollama_model or OLLAMA_MODEL}"
                    except Exception as e:
                        ollama_error = str(e)
                        try:
                            base_grams = estimate_grams_with_local_model(item)
                            model_used = "t5_local_fallback"
                        except Exception as local_e:
                            local_error = str(local_e)
                            base_grams = estimate_grams_with_heuristic(item)
                            model_used = "heuristic_fallback"
                else:
                    try:
                        base_grams = estimate_grams_with_local_model(item)
                        model_used = "t5_local"
                    except Exception as e:
                        local_error = str(e)
                        base_grams = estimate_grams_with_heuristic(item)
                        model_used = "heuristic_fallback"

            if base_grams is None:
                base_grams = 0.0

            # Ollama returns grams for the full ingredient line.
            if use_local_deberta:
                # DeBERTa predicts for normalized single-item phrasing, so scale by quantity.
                total_grams = base_grams * quantity_value
            elif (not use_local_t5) and USE_OLLAMA_GRAMS and not ollama_error:
                total_grams = base_grams
            else:
                total_grams = base_grams * quantity_value

            result = {
                "raw": text,
                "quantity": quantity_value,
                "base_prediction": round(float(base_grams), 1),
                "total_prediction": round(float(total_grams), 1),
                "model_used": model_used
            }
            if ollama_error:
                result["ollama_error"] = ollama_error
            if local_error:
                result["local_model_error"] = local_error
            if fallback_error:
                result["fallback_error"] = fallback_error
            if t5_trace:
                # Show how T5 prediction was produced when local T5 is used.
                result["t5_trace"] = {
                    **t5_trace,
                    "quantity_multiplier": quantity_value,
                    "final_total_prediction": total_grams,
                }
            if deberta_trace:
                result["deberta_trace"] = deberta_trace
            results.append(result)

        return jsonify({"predicted": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)


