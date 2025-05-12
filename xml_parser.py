from bs4 import BeautifulSoup
import json
import pandas as pd
import re

# Load XML content
xml_path = "carfilzomib_xml/c754fb7f-d170-45b5-9c6c-6d1468f6b6a8.xml"
with open(xml_path, "r", encoding="utf-8") as file:
    xml_content = file.read()

# Parse XML
soup = BeautifulSoup(xml_content, "xml")

# Initialize data structure
drug_data = {
    "product_name": None,
    "form": None,
    "ingredients": [],
    "interacts_with": [],
    "adverse_reactions": [],
    "mechanism_notes": [],
    "indications": []
}

# Extract basic product info
product = soup.find("manufacturedProduct")
if product:
    name_tag = product.find("name")
    if name_tag:
        drug_data["product_name"] = name_tag.text.strip()

    form_tag = product.find("formCode")
    if form_tag:
        drug_data["form"] = form_tag.get("displayName", "")

    ingredients = product.find_all("ingredient")
    for ing in ingredients:
        ing_name = ing.find("name")
        if ing_name:
            drug_data["ingredients"].append(ing_name.text.strip())

# Helper to collect section text
def collect_section_text(section):
    if section.find("text"):
        return section.find("text").get_text(separator=" ", strip=True)
    return ""

# Parse all sections and extract text content
sections = soup.find_all("section")
for section in sections:
    title_tag = section.find("title")
    title = title_tag.text.strip().upper() if title_tag else ""

    section_text = collect_section_text(section)

    if "ADVERSE" in title:
        drug_data["adverse_reactions"].append(section_text)
    elif "INTERACTION" in title:
        drug_data["interacts_with"].append(section_text)
    elif "PHARMACOLOGY" in title or "MECHANISM" in title:
        drug_data["mechanism_notes"].append(section_text)
    elif "INDICATION" in title:
        drug_data["indications"].append(section_text)

# Attempt to extract drug names mentioned in interactions
all_text = " ".join(drug_data["interacts_with"])
mentioned_drugs = re.findall(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b', all_text)
known_keywords = {"Table", "See", "Dosage", "Warnings", "Precautions"}
filtered_drugs = [d for d in mentioned_drugs if d not in known_keywords and len(d) > 2]
drug_data["interacts_with"] = list(set(filtered_drugs))

# Convert to DataFrame for review
df = pd.DataFrame([drug_data])
# import ace_tools as tools; tools.display_dataframe_to_user(name="Fixed Drug Label Extraction", dataframe=df)
# Save to JSON
json_path = "carfilzomib_data.json"
with open(json_path, "w", encoding="utf-8") as json_file:
    json.dump(drug_data, json_file, ensure_ascii=False, indent=4)