from flask import Blueprint, current_app,render_template, request, redirect, url_for, flash, session, get_flashed_messages, send_from_directory, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename, redirect
from sqlalchemy import func, or_
from sqlalchemy.orm.attributes import flag_modified
from pytube import Playlist
import os, random, json, string, uuid
# Personal Libraries
from models import db, Card, User, Report, Deck, Sleeve, PaymentHistory, Item, Episode, Match
from cardExtractor import *
from methods import get_spectator_game_rooms_list, is_valid_email, admin_required, login_required, opponent_checker, get_active_game_rooms_list, add_message_to_room, generate_room_code, allowed_file
from globals import chat_rooms, game_rooms

routes = Blueprint('routes', __name__)

@routes.route('/')
def index():
    return redirect(url_for('routes.home'))

# Register [Completed]
@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        # Validate input
        if len(username) < 3:
            flash("Username must be at least 3 characters long.", "error")
            return redirect(url_for('routes.register'))

        if len(password) < 8:
            flash("Passwords must be at least 8 characters long.", "error")
            return redirect(url_for('routes.register'))

        if password != confirmation:
            flash("Passwords do not match!", "error")
            return redirect(url_for('routes.register'))

        # Check if username or email already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists! Please login.", "error")
            return redirect(url_for('routes.register'))
        
        existing_email = User.query.filter((User.email == email)).first()
        if existing_email:
            flash("Email already exists! Please login.", "error")
            return redirect(url_for('routes.register'))

        trial_deck_cards = Card.query.filter(
            or_(
                Card.rarity.ilike("TD"),
                Card.rarity.ilike("SD")
            )
        ).all()
        unlocked_cards = [card.id for card in trial_deck_cards]  # Extract card numbers

        # god_cards = Card.query.all()
        # unlocked_cards = [card.id for card in god_cards]

        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, role='user', unlocked_cards=unlocked_cards)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('routes.login'))
    
    return render_template('register.html')

# Login [Completed]
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.username
            session['user_role'] = user.role
            return redirect(url_for('routes.home', usr=user.username))

        flash("Invalid username or password.", "error")
        return redirect(url_for('routes.login'))

    return render_template('login.html')

# Home Page [Incomplete]
@routes.route('/home', methods=['GET'])
def home():
    return render_template('home.html', username=session.get('user'))

# Anime [Incomplete]
@routes.route('/anime', methods=['GET'])
@login_required
def anime():
    return render_template('anime.html', username=session['user'])

@routes.route('/api/season/<int:season_id>', methods=['GET'])
def get_season_episodes(season_id):
    episodes = Episode.query.filter_by(season=season_id).all()
    episode_data = [{'id': ep.id, 'title': ep.title, 'video_url': ep.video_url, 'season': ep.season} for ep in episodes]
    return jsonify(episode_data)

@routes.route('/watch/<int:season_id>', methods=['GET', 'POST'])
@login_required
def season_episodes(season_id):
    return render_template('anime_watch.html')

# Card List [Complete]
@routes.route('/list', methods=['GET'])
@login_required
def card_list():
    action = 'delete'
    object = 'card'
    search_query = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    rarity_filter = request.args.get('rarity', '')
    world_filter = request.args.get('world', '')
    size_filter = request.args.get('size', '')
    attribute_filter = request.args.get('attribute', '')
    unlocked_only = request.args.get('unlocked') == 'true'

    query = Card.query

    if search_query:
        query = query.filter(Card.name.ilike(f"%{search_query}%"))
    if type_filter:
        query = query.filter(Card.type.ilike(f"%{type_filter}%"))
    if rarity_filter:
        query = query.filter(Card.rarity.ilike(f"%{rarity_filter}%"))
    if world_filter:
        query = query.filter(Card.world.ilike(f"%{world_filter}%"))
    if size_filter:
        query = query.filter(Card.size == int(size_filter))
    if attribute_filter:
        query = query.filter(Card.attribute.ilike(f"%{attribute_filter}%"))
    if unlocked_only:
        user = User.query.filter_by(username=session['user']).first()
        if user:
            unlocked_card_ids = user.unlocked_cards
            query = query.filter(Card.id.in_(unlocked_card_ids))

    cards = query.all()
    card_dicts = [card.to_dict() for card in cards]  # Ensure this is serialized as a list of dictionaries
    return render_template('list.html', username=session['user'], cards=card_dicts, search_query=search_query, action=action, object=object)

# Card Extractor for card list
@routes.route('/scrape')
@admin_required
def scrape_cards():
    try:
        scrape_all_cards()
        flash("Card data successfully updated!", "success")
    except Exception as e:
        flash(f"Error during scraping: {e}", "danger")
    return redirect(url_for('routes.cards'))

# Route to update an existing card
@routes.route('/update_card/<int:card_id>', methods=['GET', 'POST'])
@admin_required
def update_card(card_id):
    card = Card.query.get_or_404(card_id)
    action = 'update'
    object='card'
    if request.method == 'POST':
        card.card_no = request.form['card_no']
        card.name = request.form['name']
        card.rarity = request.form.get('rarity', '')
        card.world = request.form.get('world', '')
        card.attribute = request.form.get('attribute', '')
        card.size = int(request.form.get('size', 0)) if request.form.get('size') else card.size
        card.defense = int(request.form.get('defense', 0)) if request.form.get('defense') else card.defense
        card.critical = int(request.form.get('critical', 0)) if request.form.get('critical') else card.critical
        card.power = int(request.form.get('power', 0)) if request.form.get('power') else card.power
        card.ability_effect = request.form.get('ability_effect', card.ability_effect)
        card.flavor_text = request.form.get('flavor_text', card.flavor_text)
        card.illustrator = request.form.get('illustrator', card.illustrator)
        card.image_url = request.form.get('image_url', card.image_url)
        card.detail_url = request.form.get('detail_url', card.detail_url)
        card.type = request.form.get('type', card.type)

        db.session.commit()
        flash("Card updated successfully!", "success")
        return redirect(url_for('routes.card_list'))

    return render_template('update_card.html', card=card, action=action, object=object) 

@routes.route('/delete_card/<int:card_id>', methods=['POST'])
@admin_required
def delete_card(card_id):
    card = Card.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    flash("Card deleted successfully!", "success")
    return redirect(url_for('routes.card_list'))

# Shops [Incomplete]
@routes.route('/shops', methods=['GET', 'POST'])
@login_required
def shop():
    items = Item.query.all()
    return render_template('shops.html', username=session['user'], items=items)

@routes.route('/shops/make_payment', methods=['POST'])
@login_required
def make_payment():
    item_id = request.form.get('item_id')
    item_price = request.form.get('item_price')
    card_number = request.form.get('card_number')
    expiration_date = request.form.get('expiration_date')
    cvv = request.form.get('cvv')

    item = Item.query.filter_by(id=item_id).first()
    user = User.query.filter_by(username=session['user']).first()

    current_app.logger.info(f"Item ID: {item_id}, Item Price: {item_price}, Card: {card_number}, Expiry: {expiration_date}, CVV: {cvv}")

    if not item_id or not item_price or not card_number or not expiration_date or not cvv:
        return jsonify({"status": "error", "message": 'Invalid Form Data'}), 400

    try:
        payment = PaymentHistory(
            username=session['user'],
            item_id=item_id,
            item_price=float(item_price)
        )
        user.tickets += item.count
        db.session.add(payment)
        db.session.commit()
        return jsonify({"status": "success", "message": 'Payment Successful'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing payment: {e}")
        return jsonify({"status": "error", "message": 'Failed to process payment'}), 500
    
# Chat Rooms [Completed]
@routes.route('/chat', methods=['GET'])
@login_required
def chat():
    return render_template('chatrooms.html', username=session.get('user', 'Anonymous'))

@routes.route('/create_room', methods=['POST'])
@login_required
def create_room():
    raw_code = str(uuid.uuid4()).replace('-', '').upper()
    first_letter = random.choice(string.ascii_uppercase)
    room_code = first_letter + raw_code[:7]
    chat_rooms[room_code] = {"messages": []}
    return jsonify({"room_code": room_code})

@routes.route('/join_room', methods=['POST'])
@login_required
def join_room_http():
    data = request.json
    room_code = data.get('room_code')
    if not room_code or room_code not in chat_rooms:
        return jsonify({"error": "Room not found"}), 404
    return jsonify({"status": "success"})

# Arena HOME PAGE [COMPLETED]
@routes.route('/arenaHome', methods=['GET', 'POST'])
@login_required
def arenaHome():
    return render_template('arenaHome.html', username=session['user'])

# Arena LOBBY PAGE ONLY [DO NOT DO ANYTHING] [Completed]
@routes.route('/arenaLobby', methods=['GET', 'POST'])
@login_required
def arenaLobby():
    user = User.query.filter_by(username=session['user']).first()
    selected_deck = None
    if user.selected_deck_id:
        deck = Deck.query.get(user.selected_deck_id)
        if deck:
            selected_deck = deck.name

    return render_template('arenaLobby.html', username=session['user'], selected_deck=selected_deck)

@routes.route('/spectator/<room_code>')
@login_required
def spectator_join(room_code):
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        flash("User not found", "error")

    room_data = game_rooms[room_code]
    players_list = list(room_data['players'].keys())
    player1 = players_list[0]
    player2 = players_list[1]

    player1data = User.query.filter_by(username=player1).first()
    player2data = User.query.filter_by(username=player2).first()

    player1_profile = player1data.profile_image
    player2_profile = player2data.profile_image

    if player1_profile == "uploads/default_profile.jpg":
        player1_profile = "default_profile.jpg"
    else:
        player1_profile = player1data.profile_image

    if player2_profile == "uploads/default_profile.jpg":
        player2_profile = "default_profile.jpg"
    else:
        player2_profile = player2data.profile_image

    player1Sleeve = Sleeve.query.get(player1data.selected_sleeve_id)
    player2Sleeve = Sleeve.query.get(player2data.selected_sleeve_id)

    player1Sleeve = player1Sleeve.sleeve
    player2Sleeve = player2Sleeve.sleeve

    player1_deck = Deck.query.get(player1data.selected_deck_id)
    player2_deck = Deck.query.get(player2data.selected_deck_id)

    player1Flag = player1_deck.flagLink
    player2Flag = player2_deck.flagLink

    player1_buddy = Card.query.get(player1_deck.buddy_card_id)
    player2_buddy = Card.query.get(player2_deck.buddy_card_id)

    return render_template(
        'gameplay.html',
        room_code=room_code,
        player1=player1data.username,
        player1_profile=f"/uploads/{player1_profile}",
        player1_sleeve=player1Sleeve,
        player2=player2data.username,
        player2_profile=f'/uploads/{player2_profile}',
        player2_sleeve=player2Sleeve,
        player1_flag=f'/{player1Flag}',
        player2_flag=f'/{player2Flag}',
        player1_buddy=player1_buddy.image_url,
        player2_buddy=player2_buddy.image_url
    )

@routes.route('/spectator/information/<room_code>', methods=['POST'])
@login_required
def spectator_get_information(room_code):
    room_data = game_rooms[room_code]
    if not room_data:
        return jsonify({"error": "Room not found."})
    
    players_list = list(room_data['players'].keys())
    player1 = players_list[0]
    player2 = players_list[1]

    user = room_data['players'][player1]
    opponent = room_data['players'][player2]

    return jsonify({
        "user": user,
        "opponent": opponent
    })

@routes.route('/active_game_rooms', methods=['GET'])
def get_active_game_rooms():
    active_rooms = get_active_game_rooms_list()
    return jsonify(active_rooms)

@routes.route('/spectator_game_rooms', methods=['GET'])
def get_spectator_game_rooms():
    spectator_rooms = get_spectator_game_rooms_list()
    return jsonify(spectator_rooms)

@routes.route('/gameplay/<room_code>')
@login_required
def gameplay(room_code):
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        flash("User not found", "error")
        return redirect(url_for("routes.arenaLobby"))

    game_room = game_rooms.get(room_code)
    if not game_room or current_user.username not in game_room["players"]:
        flash("Invalid game room or you are not in this room", "error")
        return redirect(url_for("routes.arenaLobby"))

    opponent_name = None
    for p in game_room["players"]:
        if p != current_user.username:
            opponent_name = p
            break

    opponent = User.query.filter_by(username=opponent_name).first() if opponent_name else None

    user_sleeve = Sleeve.query.get(current_user.selected_sleeve_id)
    user_sleeve_img = user_sleeve.sleeve 

    opp_sleeve_img = None
    if opponent:
        opp_sleeve = Sleeve.query.get(opponent.selected_sleeve_id)
        if opp_sleeve:
            opp_sleeve_img = opp_sleeve.sleeve

    if current_user.profile_image == "uploads/default_profile.jpg":
        user_profile_picture = "default_profile.jpg"
    else:
        user_profile_picture = current_user.profile_image
    
    if opponent.profile_image == "uploads/default_profile.jpg":
        opponent_profile_picture = "default_profile.jpg"
    else:
        opponent_profile_picture = opponent.profile_image

    user_deck = Deck.query.get(current_user.selected_deck_id)
    opponent_deck = Deck.query.get(opponent.selected_deck_id)

    # Flags
    user_flag_img = user_deck.flagLink
    opponent_flag_img = opponent_deck.flagLink

    # Buddy
    user_buddy = Card.query.get(user_deck.buddy_card_id)
    opponent_buddy = Card.query.get(opponent_deck.buddy_card_id)

    # Used for testing
    room = game_rooms[room_code]['players']

    return render_template(
        'gameplay.html',
        room_code=room_code,
        username=current_user.username,
        user_profile=f"/uploads/{user_profile_picture}",  # or /uploads/ if needed
        user_sleeve=user_sleeve_img,
        opponent_name=opponent.username,
        opponent_profile=f'/uploads/{opponent_profile_picture}',
        opponent_sleeve=opp_sleeve_img,
        user_flag=user_flag_img,
        opponent_flag=opponent_flag_img,
        user_buddy=user_buddy.image_url,
        opponent_buddy=opponent_buddy.image_url,
        room = room
    )

@routes.route('/gameplay/gameInitialisation/<room_code>', methods=['POST'])
def gameInitialisation(room_code):
    room_data = game_rooms[room_code]
    if not room_data:
        return jsonify({"error": "Room not found."})
    
    username = session['user']
    opponent = opponent_checker(room_code, username)

    user = room_data['players'][username]
    opponent = room_data['players'][opponent]

    return jsonify({
        "user": user,
        "opponent": opponent
    })

@routes.route("/gameplay/gameInformation/<room_code>", methods=['POST'])
@login_required
def game_init(room_code):
    room_data = game_rooms[room_code]
    if not room_data:
        return jsonify({"error": "Room not found."})
    
    username = session['user']
    opponent = opponent_checker(room_code, username)

    user = room_data['players'][username]
    opponent = room_data['players'][opponent]

    return jsonify({
        "user": user,
        "opponent": opponent
    })

# Sleeves [Completed]
@routes.route('/sleeves', methods=['GET', 'POST'])
@login_required
def sleeves():
    sleeves = Sleeve.query.all()
    user = User.query.filter_by(username=session['user']).first()

    selected_sleeve = None
    if user.selected_sleeve_id:
        selected_sleeve = Sleeve.query.get(user.selected_sleeve_id)

    return render_template(
        'sleeves.html',
        username=session['user'],
        sleeves=sleeves,
        user=user,
        selected_sleeve=selected_sleeve.to_dict() if selected_sleeve else None
    )

@routes.route('/select_sleeve/<int:sleeve_id>', methods=['POST'])
@login_required
def select_sleeve(sleeve_id):
    user = User.query.filter_by(username=session['user']).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    sleeve = Sleeve.query.get(sleeve_id)
    if not sleeve:
        return jsonify({"error": "Sleeve not found"}), 404

    user.selected_sleeve_id = sleeve.id
    db.session.commit()

    return jsonify({
        "message": "Sleeve selected successfully!",
        "selected_sleeve": sleeve.to_dict()
    })

# Deck Builder [Completed]
@routes.route('/deckBuilder', methods=['GET'])
@login_required 
def deck_builder():
    decks = Deck.query.filter_by(username=session['user']).all()
    deck_dicts = [deck.to_dict() for deck in decks]

    selected_deck_id = next((deck.id for deck in decks if deck.selected), None)

    return render_template('deckBuilder.html', username=session['user'], decks=deck_dicts, selected_deck_id=selected_deck_id)

@routes.route('/deckBuilder/create_deck', methods=['POST'])
@login_required
def create_deck(): 
    username = session['user']
    deckName = request.form.get('name', '')
    flag = request.form.get('flag', '')

    if not deckName or not flag:
        return jsonify({"status": "error", "message": "Both name and flag are required."}), 400

    match flag:
        case 'Ancient World':
            flagImg = 'img/flags/AncientWorld.webp'
        case 'Danger World':
            flagImg = 'img/flags/DangerWorld.webp'
        case 'Darkness Dragon World':
            flagImg = 'img/flags/DarknessDragonWorld.webp'
        case 'Divine Guardians':
            flagImg = 'img/flags/DivineGuardians.webp'
        case 'Dragon Ein':
            flagImg = 'img/flags/DragonEin.png'
        case 'Dragon World':
            flagImg = 'img/flags/DragonWorld.webp'
        case 'Dragon Zwei':
            flagImg = 'img/flags/DragonZwei.webp'
        case 'Dungeon World':
            flagImg = 'img/flags/DungeonWorld.webp'
        case 'Hero World':
            flagImg = 'img/flags/HeroWorld.webp'
        case 'Katana World':
            flagImg = 'img/flags/KatanaWorld.webp'
        case 'Legend World':
            flagImg = 'img/flags/LegendWorld.webp'
        case 'Magic World':
            flagImg = 'img/flags/MagicWorld.webp'
        case 'Parade of Hundred Demons':
            flagImg = 'img/flags/ParadeofHundredDemons.webp'
        case 'Searing Executioners':
            flagImg = 'img/flags/SearingExecutioners.jpg'
        case 'Star Dragon World':
            flagImg = 'img/flags/StarDragonWorld.webp'
        case 'Thunder Empire':
            flagImg = 'img/flags/Thunder_Emporers_Fangs (1).jpg'
        case _:
            flagImg = 'img/CardBack.webp'  

    initial_life = 10
    initial_gauge = 2
    initial_hand_size = 6

    if flag == 'Dragon Ein':
        initial_life = 12
        initial_gauge = 2
        initial_hand_size = 4
    elif flag == 'Dragon Zwei':
        initial_life = 20
        initial_gauge = 2
        initial_hand_size = 4
    elif flag == 'Divine Guardians':
        initial_life = 11
        initial_gauge = 1
        initial_hand_size = 6
    elif flag == 'Searing Executioners':
        initial_life = 8
        initial_gauge = 4
        initial_hand_size = 6
    elif flag == 'Thunder Empire':
        initial_life = 11
        initial_gauge = 1
        initial_hand_size = 7

    try:
        new_deck = Deck(
            username=username, 
            name=deckName, 
            flag=flag, 
            flagLink=flagImg, 
            initial_life=initial_life, 
            initial_gauge=initial_gauge, 
            initial_hand_size=initial_hand_size
        )
        db.session.add(new_deck)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Create deck error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success", "message": f"Deck '{deckName}' created successfully!"})

@routes.route('/select_deck/<int:deck_id>', methods=['POST'])
@login_required
def select_deck(deck_id):
    current_user = User.query.filter_by(username=session['user']).first()

    if not current_user:
        return jsonify({"status": "error", "message": "User not found."}), 404

    Deck.query.filter_by(username=current_user.username).update({"selected": False})

    selected_deck = Deck.query.filter_by(id=deck_id, username=current_user.username).first()

    if not selected_deck:
        return jsonify({"status": "error", "message": "Deck not found."}), 404

    current_user.selected_deck_id = selected_deck.id
    selected_deck.selected = True

    db.session.commit()

    return jsonify({"status": "success", "message": f"Deck '{selected_deck.name}' has been selected."})

@routes.route('/deckBuilder/delete_deck/<int:deck_id>', methods=['POST'])
@login_required
def delete_deck(deck_id): 
    user = User.query.filter_by(username=session['user']).first()

    if not user:
        return jsonify({"status": "error", "message": "User not found."}), 404

    deck = Deck.query.filter_by(id=deck_id, username=user.username).first()

    if not deck:
        return jsonify({"status": "error", "message": "Deck not found."}), 404

    try:
        if user.selected_deck_id == deck.id:
            user.selected_deck_id = None

        db.session.delete(deck)
        db.session.commit()

        return jsonify({"status": "success", "message": f"Deck '{deck.name}' deleted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete deck: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while deleting the deck."}), 500

@routes.route('/edit_deck', methods=['GET'])
def edit_deck(): 
    user = User.query.filter_by(username=session['user']).first()
    if not user or not user.selected_deck_id:
        flash("No deck selected. Please select a deck first.", "error")
        return redirect(url_for('routes.deck_builder'))

    selected_deck = Deck.query.get(user.selected_deck_id)
    if not selected_deck:
        flash("Selected deck not found.", "error")
        return redirect(url_for('routes.deck_builder'))

    valid_flags = ["Generic", 'All']
    valid_attributes = []
    exclude_types = []
    exclude_worlds = ['Lost World']

    match selected_deck.flag:
        case 'Dragon Ein':
            valid_flags.extend(["Star Dragon World", "Darkness Dragon World", "Dragon World"])
            valid_attributes.append("Dragon")
        case 'Dragon Zwei':
            valid_flags.extend(["Star Dragon World", "Darkness Dragon World", "Dragon World"])
            valid_attributes.append("Dragon")
            exclude_types.extend(["Spell", "Impact", "Item"])   
        case 'Divine Guardians':
            valid_attributes.append("Guardians")
        case 'Parade of Hundred Demons':
            valid_attributes.append("Hundred Demons")
        case 'Thunder Empire':
            valid_attributes.append("Thunder Empire")
        case 'Searing Executioners':
            valid_attributes.append("Executioners")
        case _:
            valid_flags.append(selected_deck.flag)

    excluded_urls = [
        'https://s3-ap-northeast-1.amazonaws.com/en.fc-buddyfight.com/wordpress/wp-content/images/cardlist/s/bf_h00.png',
    ]

    all_unlocked_cards = Card.query.filter(Card.id.in_(user.unlocked_cards)).all()
    all_unlocked_cards = Card.query.filter(
        ~Card.image_url.in_(excluded_urls),
        ~Card.world.in_(exclude_worlds)
    ).all()
    search_query = request.args.get('name', '').strip().lower() if request.args.get('name') else ""

    filtered_cards = []
    for c in all_unlocked_cards:
        if exclude_types and c.type in exclude_types:
            continue

        splitted_worlds = [w.strip() for w in c.world.split('/')]

        world_ok = bool(set(splitted_worlds).intersection(valid_flags))

        attribute_ok = False
        if valid_attributes:
            for needed in valid_attributes:
                if needed.lower() in (c.attribute or '').lower():
                    attribute_ok = True
                    break

        if world_ok or attribute_ok:
            if search_query:
                if search_query in c.name.lower():
                    filtered_cards.append(c)
            else:
                filtered_cards.append(c)

    return render_template(
        'edit_deck.html',
        deck=selected_deck,
        unlocked_cards=filtered_cards, 
        search_query=search_query
    )

@routes.route('/edit_deck/get_deck', methods=['GET'])
@login_required
def get_deck(): 
    user = User.query.filter_by(username=session['user']).first()
    if not user or not user.selected_deck_id:
        return jsonify({"status": "error", "message": "No deck selected"}), 400

    selected_deck = Deck.query.get(user.selected_deck_id)
    if not selected_deck:
        return jsonify({"status": "error", "message": "Deck not found"}), 404

    valid_flags = ["Generic", 'All']
    valid_attributes = []
    exclude_types = []
    exclude_worlds = ['Lost World']

    match selected_deck.flag:
        case 'Dragon Ein':
            valid_flags.extend(["Star Dragon World", "Darkness Dragon World", "Dragon World"])
            valid_attributes.append("Dragon")
        case 'Dragon Zwei':
            valid_flags.extend(["Star Dragon World", "Darkness Dragon World", "Dragon World"])
            valid_attributes.append("Dragon")
            exclude_types.extend(["Spell", "Impact", "Item"])
        case 'Divine Guardians':
            valid_attributes.append("Guardians")
        case 'Parade of Hundred Demons':
            valid_attributes.append("Hundred Demons")
        case 'Thunder Empire':
            valid_attributes.append("Thunder Empire")
        case 'Searing Executioners':
            valid_attributes.append("Executioners")
        case _:
            valid_flags.append(selected_deck.flag)

    excluded_urls = [
        'https://s3-ap-northeast-1.amazonaws.com/en.fc-buddyfight.com/wordpress/wp-content/images/cardlist/s/bf_h00.png',
    ]

    all_unlocked_cards = Card.query.filter(Card.id.in_(user.unlocked_cards)).all()
    all_unlocked_cards = Card.query.filter(
        ~Card.image_url.in_(excluded_urls),
        ~Card.world.in_(exclude_worlds)
    ).all()
    search_query = request.args.get('name', '').strip().lower() if request.args.get('name') else ""

    filtered_cards = []
    for c in all_unlocked_cards:
        if exclude_types and c.type in exclude_types:
            continue

        splitted_worlds = [w.strip() for w in c.world.split('/')]

        world_ok = bool(set(splitted_worlds).intersection(valid_flags))

        attribute_ok = False
        if valid_attributes:
            for needed in valid_attributes:
                if needed.lower() in (c.attribute or '').lower():
                    attribute_ok = True
                    break

        if world_ok or attribute_ok:
            if search_query:
                if search_query in c.name.lower():
                    filtered_cards.append(c)
            else:
                filtered_cards.append(c)

    selected_deck_data = {
        "id": selected_deck.id,
        "username": selected_deck.username,
        "name": selected_deck.name,
        "cards": selected_deck.cards,
        "flag": selected_deck.flag,
        "selected": selected_deck.selected,
        "flagLink": selected_deck.flagLink,
        "buddy_card_id": selected_deck.buddy_card_id
    }

    unlocked_cards_data = [card.to_dict() for card in filtered_cards]

    return jsonify({
        "deck": selected_deck_data,
        "unlocked_cards": unlocked_cards_data
    })

@routes.route('/edit_deck/save', methods=['POST'])
@login_required
def save_deck(): #update
    user = User.query.filter_by(username=session['user']).first()
    if not user or not user.selected_deck_id:
        return jsonify({"status": "error", "message": "No deck selected"}), 400

    selected_deck = Deck.query.get(user.selected_deck_id)
    if not selected_deck:
        return jsonify({"status": "error", "message": "Deck not found"}), 404

    data = request.get_json()
    selected_deck.cards = data.get("cards", [])
    selected_deck.buddy_card_id = data.get("buddy_card_id")

    db.session.commit()

    return jsonify({"status": "success", "message": "Deck saved successfully!"})

# Gacha [Complete]
@routes.route('/gacha', methods=['GET', 'POST'])
@login_required
def gacha():
    return render_template('gacha.html', username=session['user'])

@routes.route('/gacha/tickets', methods=['GET'])
@login_required
def get_ticket_count():
    user = User.query.filter_by(username=session['user']).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    return jsonify({"status": "success", "tickets": user.tickets})

@routes.route('/gacha/pull', methods=['POST'])
@login_required
def gacha_pull():
    data = request.json
    pull_type = data.get('type')
    selected_world = data.get('world') 

    excluded_urls = [
        'https://s3-ap-northeast-1.amazonaws.com/en.fc-buddyfight.com/wordpress/wp-content/images/cardlist/s/bf_h00.png',
    ]

    user = User.query.filter_by(username=session['user']).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    ticket_cost = 10 if pull_type == "10x" else 1

    if user.tickets < ticket_cost:
        return jsonify({"status": "error", "message": "Not enough tickets"}), 400

    if selected_world is None or selected_world == "All":
        available_cards = Card.query.filter(
            ~Card.image_url.in_(excluded_urls)
        ).all()
    else:
        available_cards = Card.query.filter(
            Card.world.ilike(selected_world),
            ~Card.image_url.in_(excluded_urls)
        ).all()

    if not available_cards:
        return jsonify({"status": "error", "message": "No cards available for this world."}), 400

    card_count = 10 if pull_type == "10x" else 1
    pulled_cards = random.sample(available_cards, min(card_count, len(available_cards)))

    unlocked_cards = user.unlocked_cards or []
    if isinstance(unlocked_cards, str):
        unlocked_cards = json.loads(unlocked_cards)

    tickets_earned = 0
    for card in pulled_cards:
        if card.id not in unlocked_cards:
            unlocked_cards.append(card.id)
        else:
            tickets_earned += 1 

    user.unlocked_cards = unlocked_cards
    user.tickets -= ticket_cost  
    user.tickets += tickets_earned 

    flag_modified(user, "unlocked_cards")
    db.session.commit()

    return jsonify({
        "status": "success",
        "cards": [card.to_dict() for card in pulled_cards],
        "tickets": tickets_earned,
        "current_tickets": user.tickets
    })

# About Page [Incomplete]
@routes.route('/about', methods=['GET', 'POST'])
@login_required
def about():
    return render_template('about.html', username=session['user'])

# Settings [Incomplete]
@routes.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    username = User.query.filter_by(username=session['user']).first()
    email = username.email

    payments = PaymentHistory.query.filter_by(username=session['user']).all()
    payment_data = []

    for payment in payments:
        item = Item.query.filter_by(id=payment.item_id).first() 
        if item:
            payment_detail = {
                "id": payment.id,
                "tickets": item.count,
                "price": f"{payment.item_price:.2f}",
                "date": payment.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            }
        payment_data.append(payment_detail)

    matches = Match.query.filter_by(username=session['user']).all()
    match_data = [
        {
            "username": match.username,
            "winner": match.winner,
            "loser": match.loser,
            'date': match.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        } for match in matches
    ]

    return render_template(
        'settings.html',
        username=username,
        email=email,
        payments=payment_data,
        matches=match_data
    )

@routes.route('/update_username', methods=['POST'])
@login_required
def update_username():
    user = User.query.filter_by(username=session['user']).first()

    if not user:
        return jsonify({"status": "error", "message": "User not found."})

    new_username = request.form.get('username')
    if not new_username or len(new_username) < 3:
        return jsonify({"status": "error", "message": "Username must be at least 3 characters long."})

    if User.query.filter_by(username=new_username).first():
        return jsonify({"status": "error", "message": "Username already taken."})

    user.username = new_username
    Deck.query.filter_by(username=session['user']).update({"username": new_username})
    PaymentHistory.query.filter_by(username=session['user']).update({"username": new_username})
    session['user'] = new_username
    db.session.commit()
    
    db.session.commit()

    return jsonify({"status": "success", "message": "Username updated successfully!"})

@routes.route('/update_email', methods=['POST'])
@login_required
def update_email():
    try:
        username = User.query.filter_by(username=session['user']).first()
        if not username:
            return jsonify({"status": "error", "message": "User not found."})

        new_email = request.form.get('email')
        if not new_email or not is_valid_email(new_email):
            return jsonify({"status": "error", "message": "Invalid email address."})

        if User.query.filter_by(email=new_email).first():
            return jsonify({"status": "error", "message": "Email already in use."})

        username.email = new_email
        db.session.commit()

        return jsonify({"status": "success", "message": "Email updated successfully!"})

    except Exception as e:
        db.session.rollback()
        print(f"Error updating email: {e}")
        return jsonify({"status": "error", "message": "An internal error occurred. Please try again later."})

@routes.route('/update_password', methods=['POST'])
@login_required
def update_password():
    new_password = request.form.get('password')
    confirmation = request.form.get('confirmation')

    if not new_password or len(new_password) < 8:
        return jsonify({"status": "error", "message": "Passwords must be at least 8 characters long!"}), 400

    if new_password != confirmation:
        return jsonify({"status": "error", "message": "Passwords do not match!"}), 400

    try:
        username = User.query.filter_by(username=session['user']).first()
        if not username:
            return jsonify({"status": "error", "message": "User not found!"}), 404

        username.password = generate_password_hash(new_password)
        db.session.commit()

        return jsonify({"status": "success", "message": "Password updated successfully!"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error updating password: {e}")
        return jsonify({"status": "error", "message": "An internal error occurred. Please try again later."}), 500

@routes.route('/delete_user', methods=['POST'])
def delete_user():
    user = User.query.filter_by(username=session['user']).first()

    if user:
        Deck.query.filter_by(username=user.username).delete()
        PaymentHistory.query.filter_by(username=user.username).delete()
        db.session.delete(user)
        db.session.commit()

        session.clear()
        flash("Account has been successfully deleted.")
        return redirect(url_for('routes.login'))

    return jsonify({"status": "error", "message": "User not found. Unable to delete account."}), 500

@routes.route('/user_report', methods=['POST'])
@login_required
def user_report():
    report_type = request.form.get('report-type')
    user_being_reported = request.form.get('user_being_reported', '')
    user_reporting = session['user']
    detail = request.form.get('detail', '')

    if user_being_reported:
        existing_user = User.query.filter_by(username=user_being_reported).first()
        if not existing_user:
            return jsonify({"status": "error", "message": "User being reported does not exist."})

    if not report_type:
        return jsonify({"status": "error", "message": "Report type is required."}), 400
    if not detail:
        return jsonify({"status": "error", "message": "Details are required."}), 400

    try:
        report_card = Report(
            user_reporting=user_reporting,
            user_being_reported=user_being_reported if user_being_reported else None,
            report_type=report_type,
            detail=detail
        )
        db.session.add(report_card)
        db.session.commit()
        return jsonify({"status": "success", "message": "Report submitted successfully."}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"An error submitting your report occurred: {str(e)}"}), 500
    except:
        return jsonify({"status": "error", "message": f"An error submitting your report occurred: {str(e)}"}), 500
    finally:
        db.session.close()

@routes.route('/update_profile_picture', methods=['POST'])
@login_required
def update_profile_picture():
    username = User.query.filter_by(username=session['user']).first()
    if not username:
        return jsonify({"status": "error", "message": "User not found."}), 404

    if 'profile_picture' not in request.files:
        return jsonify({"status": "error", "message": "No file selected."}), 400

    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected."}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(f"{username.username}.{file.filename.rsplit('.', 1)[1].lower()}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        try:
            old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], username.profile_image.split('/')[-1])
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        except Exception as e:
            print(f"Error deleting old profile picture: {e}")

        file.save(filepath)
        username.profile_image = f"profile_images/{filename}"
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Profile picture updated successfully!",
            "image_path": f"/uploads/profile_images/{filename}"
        })

    return jsonify({"status": "error", "message": "Invalid file type. Please upload a valid image."}), 400

# Admin Page [Incomplete]
@routes.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin():
    users = User.query.all()
    payments = PaymentHistory.query.all()
    total_tickets_bought = 0
    user_count = len(users)

    # find total income from Payments
    total_income = db.session.query(func.sum(PaymentHistory.item_price)).scalar()
    total_income = total_income if total_income else 0

    # find total tickets bought from payments
    for payment in payments:
        tickets_bought = Item.query.filter_by(id=payment.item_id).first()
        if tickets_bought:
            total_tickets_bought += tickets_bought.count

    # find total number of matches played
    total_matches = db.session.query(func.count(Match.id)).scalar()
    total_matches = total_matches // 2 if total_matches else 0

    return render_template(
        'admin.html',
        username=session['user'],
        users=users,
        total_users=user_count,
        total_cash=f"{total_income:.2f}",
        total_tickets_bought=total_tickets_bought,
        total_matches=total_matches
    )

@routes.route('/admin/payment_history', methods=['GET'])
@login_required
def get_payment_history():
    all_history = PaymentHistory.query.all()
    chart_data = []
    for record in all_history:
        x_value = int(record.timestamp.timestamp() * 1000)
        y_value = record.item_price
        chart_data.append({"x": x_value, "y": y_value})

    return jsonify({"payment_data": chart_data})

@routes.route('/admin/match_history', methods=['GET'])
@login_required
def get_match_history():
    all_matches = Match.query.all()
    chart_data = []
    for match in all_matches:
        x_value = int(match.timestamp.timestamp() * 1000)
        y_value = 1
        chart_data.append({"x": x_value, "y": y_value})

    return jsonify({"match_data": chart_data})

@routes.route('/admin/get_payment', methods=['GET'])
@admin_required
def get_payments():
    payments = PaymentHistory.query

    user_query = request.args.get('user-payment', '')
    if user_query:
        payments = payments.filter(PaymentHistory.username.ilike(f"%{user_query}%"))

    price_query = request.args.get('payment-amount', '')
    if price_query:
        payments = payments.filter(PaymentHistory.item_price == price_query)

    count_query = request.args.get('item-count', '')
    if count_query:
        count_query = int(count_query)
        item = Item.query.filter_by(id=count_query).first()
        item_id = item.id if item else count_query
        payments = payments.filter(PaymentHistory.item_id == item_id)

    payments = payments.all()

    payment_data = [
        {
            "id": payment.id,
            "username": payment.username,
            "item_id": payment.item_id,
            "item_price": payment.item_price,
            "date": payment.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for payment in payments
    ]

    for payment in payment_data:
        item = Item.query.filter_by(id=payment['item_id']).first()
        payment['item_id'] = item.count

    return jsonify({"payments": payment_data})

@routes.route('/admin/get_users', methods=['GET'])
@admin_required
def get_users():
    search_query = request.args.get('username', '')
    query = User.query
    if search_query:
        query = query.filter(
            User.username.ilike(f"%{search_query}%")
        )
    users = query.all()
    user_data = [
        {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "wins": user.wins,
            "losses": user.losses,
            "tickets": user.tickets
        }
        for user in users
    ]
    return jsonify({"users": user_data})

@routes.route('/admin/get_reports', methods=['GET'])
@admin_required
def get_reports():
    report_query = Report.query
    user_reporting_filter = request.args.get('user-reporting', '')
    reported_user_filter = request.args.get('reported-user', '')
    report_type_filter = request.args.get('report-type', '')

    if user_reporting_filter:
        report_query = report_query.filter(Report.user_reporting.ilike(f"%{user_reporting_filter}%"))
    if reported_user_filter:
        report_query = report_query.filter(Report.user_being_reported.ilike(f"%{reported_user_filter}%"))
    if report_type_filter:
        report_query = report_query.filter(Report.report_type.ilike(f"%{report_type_filter}%"))

    reports = report_query.all()
    reports_data = [
        {
            "id": report.id,
            "user_reporting": report.user_reporting,
            "user_being_reported": report.user_being_reported,
            "report_type": report.report_type,
            "detail": report.detail,
        }
        for report in reports
    ]
    return jsonify({"reports": reports_data})

@routes.route('/admin/get_sleeves', methods=['GET'])
@admin_required
def get_sleeves():
    sleeves_query = Sleeve.query

    sleeve_search = request.args.get('search_sleeve')
    if sleeve_search:
        sleeves_query = sleeves_query.filter(Sleeve.sleeve_type.ilike(f"%{sleeve_search}%"))

    sleeves = sleeves_query.all()
    sleeve_data = [
        {
            "id": sleeve.id,
            "sleeve": sleeve.sleeve,
            "sleeve_type":sleeve.sleeve_type
        }
        for sleeve in sleeves
    ]
    return jsonify({"sleeves": sleeve_data})

@routes.route('/admin/get_anime', methods=['GET'])
@admin_required
def get_anime():
    anime_query = Episode.query

    anime_search = request.args.get('search_anime')
    if anime_search:
        anime_query = anime_query.filter(Episode.season.ilike(f"%{anime_search}%"))
    episode_search = request.args.get('search_anime_episode')
    if episode_search:
        anime_query = anime_query.filter(func.lower(Episode.title) == episode_search.lower())


    animes = anime_query.all()
    anime_data = [
        {
            "id": anime.id,
            "ep_number": anime.title,
            "anime_season": anime.season,
            "video_url": anime.video_url
        }
        for anime in animes
    ]
    return jsonify({"animes": anime_data})

@routes.route('/admin/add_anime', methods=['POST'])
@admin_required
def add_anime():
    episode = request.form.get('anime-episode')
    video = request.form.get('anime-episode-link')
    season = request.form.get('anime-season')

    new_anime = Episode(title=episode, video_url=video, season=season)
    db.session.add(new_anime)
    db.session.commit()

    return jsonify({"status": "success", "message": "Anime added successfully!"}), 200

@routes.route('/admin/delete_anime/<id>', methods=['POST'])
@admin_required
def delete_anime(id):
    anime = Episode.query.filter_by(id=id).first()

    if not anime:
        return jsonify({"status": "error", "message": "Anime not found"}), 404

    db.session.delete(anime)
    db.session.commit()
    return jsonify({"status": "success", "message": "Anime deleted successfully!"}), 200

@routes.route('/admin/update_anime/<id>', methods=['POST'])
@admin_required
def update_anime(id):
    anime = Episode.query.filter_by(id=id).first()

    if not anime:
        return jsonify({"status": "error", "message": "Anime not found"}), 404

    episode = request.form.get('update-episode')
    video = request.form.get('update-url')
    season = request.form.get('update-season')

    if episode:
        anime.title = episode
    if video:
        anime.video_url = video
    if season:
        anime.season = season

    db.session.commit()
    return jsonify({"status": "success", "message": "Anime updated successfully!"}), 200

@routes.route('/admin/delete_report/<id>', methods=['DELETE'])
@admin_required
def delete_report(id):
    if session.get('user_role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized access"}), 403

    report = Report.query.filter_by(id=id).first()
    if not report:
        return jsonify({"status": "error", "message": "Report not found"}), 404

    try:
        db.session.delete(report)
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": f"Report with ID {id} deleted successfully",
            "deleted_report": report.to_dict()  
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Failed to delete report: {str(e)}"}), 500

@routes.route('/admin/update_user', methods=['POST'])
@admin_required
def update_user():
    try:
        data = request.form
        username = data.get('username')

        if not username:
            return jsonify({"status": "error", "message": "Username is required"}), 400

        user = User.query.filter_by(username=username).first()

        if session['user'] != 'Featcrazyball':
            if user.role == 'admin':
                return jsonify({'status':'error', 'message':'Unaurthorised action.'}), 403

        email = data.get('email', user.email)
        if email and '@' not in email:  
            return jsonify({"status": "error", "message": "Invalid email format"}), 400
        user.email = email

        role = data.get('role', user.role)
        if role not in ['user', 'admin']: 
            return jsonify({"status": "error", "message": "Invalid role"}), 400
        user.role = role

        try:
            user.wins = int(data.get('wins', user.wins))
            user.losses = int(data.get('losses', user.losses))
            user.tickets = int(data.get('tickets', user.tickets))
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid numeric input"}), 400

        new_username = data.get('new_username')
        if new_username and new_username != username:
            if User.query.filter_by(username=new_username).first():
                return jsonify({"status": "error", "message": "Username already taken"}), 400

            Deck.query.filter_by(username=username).update({"username": new_username})
            user.username = new_username

        db.session.commit()
        return jsonify({"status": "success", "message": "User updated successfully."}), 200

    except Exception as e:
        current_app.logger.error(f"Update user error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@routes.route('/admin/delete_account/<username>', methods=['POST'])
@admin_required
def delete_account(username):
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    if session['user'] != 'Featcrazyball':
        if user.role == 'admin':
            return jsonify({'status':'error', 'message':'Unaurthorised action.'}), 403

    if user.username == session['user']:
        return jsonify({"message": "You cannot delete yourself", "status": "error"}), 404

    try:
        Deck.query.filter_by(username=username).delete()
        PaymentHistory.query.filter_by(username=username).delete()

        db.session.delete(user)
        db.session.commit()

        return jsonify({"status": "success", "message": f"User {username} and their decks deleted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete user: {e}")
        return jsonify({"status": "error", "message": f"Failed to delete user: {str(e)}"}), 500

@routes.route('/admin/sleeves', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_sleeves():
    if request.method == 'POST':
        if 'sleeve_image' in request.files and 'sleeve_type' in request.form:
            file = request.files['sleeve_image']
            sleeve_type = request.form.get('sleeve_type')

            if file.filename == '':
                return jsonify({"status": "error", "message": "No file selected."}), 200

            if not allowed_file(file.filename):
                return jsonify({"status": "error", "message": f"File type not allowed"}), 200

            sleeve_count = Sleeve.query.count() + 1
            original_filename = file.filename
            extension = original_filename.rsplit('.', 1)[1].lower()
            new_filename = f"_Sleeve{sleeve_count}.{extension}"
            filepath = os.path.join(current_app.config['UPLOAD_SLEEVE'], new_filename)
            file.save(filepath)

            new_sleeve = Sleeve(sleeve=f"img/sleeves/{new_filename}", sleeve_type=sleeve_type)
            db.session.add(new_sleeve)
            db.session.commit()

            return jsonify({"message": "Sleeve added successfully!", "sleeve": new_sleeve.to_dict()})

        return jsonify({"error": "Invalid data"}), 400

@routes.route('/admin/sleeves/delete/<int:sleeve_id>', methods=['POST'])
@login_required
@admin_required
def delete_sleeve(sleeve_id):
    sleeve = Sleeve.query.get(sleeve_id)
    if not sleeve:
        return jsonify({"error": "Sleeve not found"}), 404

    sleeve_path = os.path.join(current_app.config['UPLOAD_SLEEVE'], os.path.basename(sleeve.sleeve))

    if os.path.exists(sleeve_path):
        os.remove(sleeve_path)

    db.session.delete(sleeve)
    db.session.commit()

    return jsonify({"message": "Sleeve deleted successfully!"})

@routes.route('/update_session', methods=['POST'])
def update_session():
    usr = request.args.get('usr')
    
    if usr:
        user = User.query.filter_by(username=usr).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        session['user'] = user.username
    elif 'user' in session:
        current_user = User.query.filter_by(username=session['user']).first()
        if not current_user:
            return jsonify({"status": "error", "message": "Session user not found"}), 404
        
        session['user'] = current_user.username
    else:
        return jsonify({"status": "error", "message": "User not logged in"}), 403

    session.modified = True
    return jsonify({"status": "success", "message": "Session updated successfully"})

# Logout
@routes.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('routes.login'))

@routes.route('/uploads/profile_images/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@routes.route('/error')
def error():
    return render_template('error.html')

@routes.route('/trigger-error/<int:error>')
def trigger_404(error):
    abort(error)  