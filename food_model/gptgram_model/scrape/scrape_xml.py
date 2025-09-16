from recipe_scrapers import SCRAPERS, scrape_me
from ingredient_parser import parse_ingredient
from bs4 import BeautifulSoup
import requests
import time
import re

def extract_recipe_links(sitemap_url):
    response = requests.get(sitemap_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch sitemape: {sitemap_url}")
    
    soup = BeautifulSoup(response.content, 'xml')
    loc_tags = soup.find_all('loc')

    recipe_links = [
        loc.text for loc in loc_tags
        if '/recipe/' in loc.text
    ]
    return recipe_links

if __name__ == "__main__":
    recipe_urls = []
    for i in range(1,5):
        sitemap_url = f"https://www.allrecipes.com/sitemap_{i}.xml" # use f" {}""
        urls = extract_recipe_links(sitemap_url)
        recipe_urls.extend(urls)
    with open("recipe_links.txt", "w") as f:
        for url in recipe_urls:
            f.write(url + "\n")
    print(f"Saved {len(recipe_urls)} recipe links to recipe_links.txt")
