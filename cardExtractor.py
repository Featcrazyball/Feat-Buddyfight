import requests, re
from bs4 import BeautifulSoup
from models import db, Card  # Import models and db instance

def clean_description(text):
    cleaned_text = re.sub(r'(<br\s*/?>)+', ' ', text, flags=re.IGNORECASE)
    parts = cleaned_text.split('■')
    seen = set()
    unique_parts = []
    for part in parts:
        if part not in seen:
            seen.add(part)
            unique_parts.append(part)
    return '■'.join(unique_parts).strip()

#get some details from site
def scrape_card_details(card_url):
    response = requests.get(card_url)
    soup = BeautifulSoup(response.content, "html.parser")

    card_details = {}
    table = soup.find("table", class_="status")

    if table:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["th", "td"])
            if len(cells) == 4:
                card_details[cells[0].text.strip()] = cells[1].text.strip()
                card_details[cells[2].text.strip()] = cells[3].text.strip()
            elif len(cells) == 2:
                card_details[cells[0].text.strip()] = cells[1].text.strip()

    # Add a check to ensure the image exists
    image_div = soup.find("div", class_="image_v")
    is_horizontal = False  
    if not image_div: 
        image_div = soup.find("div", class_="image_h")
        is_horizontal = True

    card_details["image_url"] = (
        image_div.img["src"] if image_div and image_div.img else "/static/images/default_card.png"
    )
    card_details["is_horizontal"] = is_horizontal  # Add flag to indicate orientation

    # Add checks to ensure the card name exists
    card_details["name"] = soup.find("p", class_="card_name").text.strip() if soup.find("p", class_="card_name") else "Unknown Card"

    # Add a check to ensure the rarity exists
    rarity_img = soup.find("p", class_="rare")
    card_details["rarity"] = rarity_img.img["alt"] if rarity_img and rarity_img.img else "Unknown Rarity"

    # Add a check to ensure the type exists
    type_label = soup.find(string=re.compile("Card Type", re.IGNORECASE))
    card_details["type"] = type_label.find_next("td").text.strip() if type_label and type_label.find_next("td") else "No Type"

    # Add checks for ability_effect and flavor_text
    ability_effect_th = soup.find("th", string="Ability/Effect")
    card_details["ability_effect"] = ability_effect_th.find_next("td").decode_contents() if ability_effect_th else "No ability/effect"

    flavor_text_th = soup.find("th", string="Flavor Text")
    card_details["flavor_text"] = flavor_text_th.find_next("td").text.strip() if flavor_text_th else "No flavor text"

    # Add check for illustrator
    illustrator_th = soup.find("th", string="Illustrator")
    card_details["illustrator"] = illustrator_th.find_next("td").text.strip() if illustrator_th else "Unknown Illustrator"

    # Finally, include the detail_url
    card_details["detail_url"] = card_url

    return card_details

def scrape_all_cards():
    base_list_url = "https://en.fc-buddyfight.com/cardlist/list/?id={}"
    base_detail_url = "https://en.fc-buddyfight.com/cardlist/cardDetail/?cardno={}"

    for list_id in range(1, 44):
        list_url = base_list_url.format(list_id)
        response = requests.get(list_url)
        soup = BeautifulSoup(response.content, "html.parser")
        card_links = soup.find_all("a", href=re.compile("/cardlist/cardDetail/"))

        for card_link in card_links:
            card_no = card_link["href"].split("=")[-1]
            detail_url = base_detail_url.format(card_no)
            try:
                card_data = scrape_card_details(detail_url)

                # Extract the data for the fields and handle invalid values
                size = card_data.get("Size", "0")
                power = card_data.get("Power", "0")
                critical = card_data.get("Critical", "0")
                defense = card_data.get("Defense", "0")

                # Ensure these fields are integers or default to 0 if invalid
                size = int(size) if size.isdigit() else 0
                power = int(power) if power.isdigit() else 0
                critical = int(critical) if critical.isdigit() else 0
                defense = int(defense) if defense.isdigit() else 0

                # Check if the card already exists in the database
                existing_card = Card.query.filter_by(card_no=card_data.get("Card No.")).first()
                if not existing_card:
                    new_card = Card(
                        card_no=card_data.get("Card No."),
                        name=card_data.get("name"),
                        rarity=card_data.get("rarity"),
                        world=card_data.get("World"),
                        attribute=card_data.get("Attribute"),
                        size=size,
                        defense=defense,
                        critical=critical,
                        power=power,
                        ability_effect = clean_description(card_data.get("ability_effect")),
                        flavor_text=card_data.get("flavor_text"),
                        illustrator=card_data.get("illustrator"),
                        image_url=card_data.get("image_url"),
                        detail_url=card_data.get("detail_url"),
                        type=card_data.get("type"),
                        is_horizontal=card_data.get("is_horizontal"),
                    )
                    db.session.add(new_card)
                    db.session.commit()

                    print(f"Inserted: {card_no}")
            except Exception as e:
                print(f"Error processing card {card_no}: {e}")
                
