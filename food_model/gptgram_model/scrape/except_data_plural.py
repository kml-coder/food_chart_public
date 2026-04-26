from recipe_scrapers import scrape_me, WebsiteNotImplementedError
from ingredient_parser import parse_ingredient
from fractions import Fraction
import json, csv, time, inflect



t= inflect.engine()

# TODO
# 1. gram으로 변환 불가한거 찾고 그것만 포함시키기, 그리고 만약 fl oz같은거는 항상 액체니까 그런거 gram으로 변환하기 힘들거 같다 생각하지 말고 그냥 그것도 제외하기
unitmap = {
        # --gram으로 변환 가능한 것들--

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

        # Pound
        'pound': 453.6,
        'lb': 453.6,
        'lbs': 453.6,

        # --부피 단위지만 주로 쓰이는게 액체라 환산 가능한 것들--

        # Fluid ounce (1 fl oz ≈ 2 tbsp)
        'fluid ounce': 30,
        'fluid ounces': 30,
        'fl oz': 30,

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

        # --쓰이는 것이 액체, 고체 다 달라서 데이타 셋에 포함되어야 할 것들--

        # # Cup
        # 'cup': 240,
        # 'cups': 240,
        # 'c': 240,

        # # Tablespoon (base unit)
        # 'tablespoon': 15,
        # 'tablespoons': 15,
        # 'tbsp': 15,
        # 'tbsps': 15,

        # # Teaspoon
        # 'teaspoon': 5,
        # 'teaspoons': 5,
        # 'tsp': 5,
        # 'tsps': 5,
        
    }

def safe_text(field):
    if isinstance(field, list):
        return field[0].text if field else ''
    elif hasattr(field, 'text'):
        return field.text
    return ''

def singularize_name(name:str) -> str:
    words = name.split()
    return " ".join([t.singular_noun(w) if t.singular_noun(w) else w for w in words])

def parse_and_filter_ingredient(line):

    parsed = parse_ingredient(line)
    
    # size 정해짐
    size = safe_text(parsed.size)
    # name 정해짐
    name = safe_text(parsed.name)
    name = singularize_name(name)
    name = name.lower()
    quantity = ''
    unit = ''

    # amount 항목 자체가 없으면 아예 제외 salt and pepper 같은거-서버에서는 except 데이터로 들어갈것
    if not parsed.amount:
        return None
    # a bunch of parsley

    #quantity, unit 정하는중
    matched_amount = None

    for amt in parsed.amount:
        if str(amt.unit).lower() in unitmap:
            return None
    amt = parsed.amount[0]

    if amt and hasattr(amt, 'quantity_max') and isinstance(amt.quantity_max, (int, float, Fraction)):
        q = float(amt.quantity_max)
    elif amt and isinstance(amt.quantity, Fraction):
        q = float(amt.quantity)
    elif amt and amt.quantity:
        try:
            q = float(amt.quantity)
        except ValueError:
            # 범위 문자열 등으로 float 변환 실패 → 그냥 1로 처리
            q = 1
    else:
        # quantity 자체가 없으면 빈 문자열 처리
        q = ''

    if isinstance(q, float):
        q = round(q,2)
        quantity = int(q) if q.is_integer() else q
    else:
        quantity = q


    if amt.unit: 
        unit = str(amt.unit).lower()

    unit = singularize_name(unit)

    cleaned = " ".join(str(x) for x in [quantity, unit, size, name] if x).strip() # 이거 중요 " ".join(x for x in [a,b,c,d] if x) 해서 있는것만 추가, 없는 거는 추가 안함
    return [cleaned] 
        
    

def extract_except_raws_from_url(url):
    try:
        scraper = scrape_me(url)
        ingredients = scraper.ingredients()
        return [
            parsed_raw for line in ingredients
            if (parsed_raw := parse_and_filter_ingredient(line)) is not None # 이 줄이 의미하는건 parsed_raw가 true 면
        ]
    except WebsiteNotImplementedError:
        print({"[skip]: Not supported recipe Website."}),
    except Exception as e:
        print(f"[error] : Failed on {url}: {e}")
    return []

def save_gram_request_json(raws, filename = "plural.json"):
    out = {raw[0]: " " for raw in raws}
    with open(filename, "w") as f:
        json.dump(out,f,indent=2)
if __name__ == '__main__':
    with open("recipe_links.txt", "r") as f:
        urls = []
        for _ in range(30):
            line = f.readline()
            if not line:
                break
            urls.append(line.strip())
    # with open("recipe_links.txt", "r") as f:
    #     urls = [line.strip() for line in f if line.strip()]

    all_raws = []
    for i, url in enumerate(urls):
        print(f"[{i+1}/{len(urls)}] Scraping: {url}")
        raws = extract_except_raws_from_url(url)
        all_raws.extend(raws)
    save_gram_request_json(all_raws)
    print(f"Save {len(all_raws)} entries to gram_request.json")
    #print(parse_and_filter_ingredient("0.5 to 1 tsp salt"))
