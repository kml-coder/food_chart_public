from flask import Flask,request,jsonify
from flask_cors import CORS
from recipe_scrapers import scrape_me, WebsiteNotImplementedError
from ingredient_parser import parse_ingredient
from fractions import Fraction
from bs4 import BeautifulSoup

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
        # Ounce-based
        'ounce': 2,
        'ounces': 2,
        'oz': 2,
        'onze': 2,  # likely a typo of "ounce"

        # Pound
        'pound': 32,
        'lb': 32,
        'lbs': 32,

        # Cup
        'cup': 16,
        'cups': 16,
        'c': 16,

        # Tablespoon (base unit)
        'tablespoon': 1,
        'tablespoons': 1,
        'tbsp': 1,
        'tbsps': 1,

        # Teaspoon
        'teaspoon': 1 / 3,
        'teaspoons': 1 / 3,
        'tsp': 1 / 3,
        'tsps': 1 / 3,

        # Fluid ounce (1 fl oz ≈ 2 tbsp)
        'fluid ounce': 2,
        'fluid ounces': 2,
        'fl oz': 2,

        # Pint (1 pt = 32 tbsp)
        'pint': 32,
        'pt': 32,

        # Quart (1 qt = 64 tbsp)
        'quart': 64,
        'qt': 64,

        # Gallon (1 gal = 256 tbsp)
        'gallon': 256,
        'gal': 256,

        # Metric (approximate to tbsp) # 이거는 되도록 제외하기
        'milliliter': 1 / 15,
        'milliliters': 1 / 15,
        'ml': 1 / 15,

        'liter': 1000 / 15,
        'liters': 1000 / 15,
        'l': 1000 / 15, # 이거는 조심하기 l가 알파벳 하나라 좀 오류 작동할 수 있을듯
    }

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

    amount = None
    for amt in amounts:
        if str(amt.unit).lower() in unitmap:
            amount = amt
            break
    if not amount:
        amount = amounts[0]

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)


