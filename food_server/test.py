from flask import Flask,request,jsonify
from flask_cors import CORS
from recipe_scrapers import scrape_me, WebsiteNotImplementedError
from ingredient_parser import parse_ingredient
from fractions import Fraction
from bs4 import BeautifulSoup

import requests, json, csv, re, time

def parse_ingredient_line(line):
    parsed = parse_ingredient(line)
    amounts = parsed.amount
    name = parsed.name[0].text if parsed.name else ''


    if not amounts:
        return { # except data
            "name": name,
            "value": 0,
            "unit": "",

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
        "quantity": quantity,
        "raw": line,
        "raw_text": parsed
    }

lines = [
    "For the Crust",
    "5 tablespoons unsalted butter, melted",
    "For the Filling",
    "Sponsored By Vail Resorts Management Company",
    "Sponsored Video",
    "Watch to learn more",
    "Special equipment: 9- or 10-inch springform pan; 18-inch heavy-duty aluminum foil (see Pro Tip)"
]

for ing in lines: print(parse_ingredient(ing))

