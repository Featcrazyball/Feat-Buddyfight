from flask import session, redirect, url_for, flash, request
from functools import wraps
from flask_socketio import emit
import random, string, re
# Personal
from globals import ALLOWED_EXTENSIONS, game_rooms, chat_rooms
from models import db, Card, User, Report, Deck, Sleeve, PaymentHistory, Item

# Role-based access control decorators for Admin required
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return redirect(url_for('routes.home'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(func):
    @wraps(func) 
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('routes.login'))
        return func(*args, **kwargs) 
    return wrapper

# Some useful methods so i dont need to keep copy and pasting
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def select_deck(self, deck_id):
    deck = Deck.query.get(deck_id)
    if deck and deck.username == self.username: 
        self.selected_deck_id = deck.id
        db.session.commit()
        return True
    return False

def deselect_deck(self):
    self.selected_deck_id = None
    db.session.commit()

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))

def get_active_game_rooms_list():
    return [
        {
            "room_code": room_code,
            "creator_username": room_data["creator_username"],
            "creator_profile_picture": room_data["creator_profile_picture"],
        }
        for room_code, room_data in game_rooms.items()
        if len(room_data["players"]) < 2  # Exclude full rooms
    ]

def add_message_to_room(room, username, message):
    chat_rooms[room]["messages"].append({
        "username": username,
        "message": message
    })
    if len(chat_rooms[room]["messages"]) > 500:
        chat_rooms[room]["messages"].pop(0)

def opponent_checker(room_code, username):
    room_data = game_rooms[room_code]
    if not room_data or username not in room_data["players"]:
        emit('error', {"message": "Unexpected error joining room."}, room=request.sid)
        return

    opponent = None
    for player in room_data["players"]:
        if player != username:
            opponent = player
            return opponent

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email)

# Area Methods
def shuffle_deck(deck):
    random.shuffle(deck)
    return deck

def draw_cards(deck, count):
    drawn_cards = deck[:count]
    remaining_deck = deck[count:]
    username = session['user']
    if len(remaining_deck) < 1:
        emit('mini_chat_message', {
            'sender': 'System',
            'message': f"{username} has run out of cards in their deck."
        }, room=request.sid)
        return
    return drawn_cards, remaining_deck

def get_card_data(card_ids):
    unique_ids = set(card_ids)
    cards = Card.query.filter(Card.id.in_(unique_ids)).all()
    card_map = {c.id: c.to_dict() for c in cards}

    result = []
    for cid in card_ids:
        if cid in card_map:
            result.append(card_map[cid])
    return result

def remove_card_from_zone(card_data, from_zone, room_code, spell_id=None):
    username = session['user']

    match from_zone:
        case _ if from_zone in ("left", "center", "right", "item"):
            occupant = game_rooms[room_code]['players'][username].get(from_zone)
            if occupant and occupant.get('id') == card_data.get('id'):
                card_soul = occupant.get('soul', [])
                if card_soul:
                    dropzone = game_rooms[room_code]['players'][username].get("dropzone", [])

                    for soul_card in card_soul:
                        soul_card_id = soul_card.get('id')
                        if not any(existing_card.get('id') == soul_card_id for existing_card in dropzone):
                            dropzone.append(soul_card)
                            dropzone.remove(soul_card)
                    card_soul.clear()

                game_rooms[room_code]['players'][username][from_zone] = None

        case "hand":
            hand = game_rooms[room_code]['players'][username]['current_hand']
            if card_data in hand:
                hand.remove(card_data)
                game_rooms[room_code]['players'][username]['current_hand_size'] -= 1

        case "dropzone":
            dropzone = game_rooms[room_code]['players'][username]["dropzone"]
            if card_data in dropzone:
                dropzone.remove(card_data)

        case "spells":
            spells = game_rooms[room_code]['players'][username]["spells"]
            if card_data in spells:
                spells.remove(card_data)

        case 'spell-soul':
            spells = game_rooms[room_code]['players'][username]['spells']
            the_spell = next((s for s in spells if s['id'] == spell_id), None)
            if the_spell and "soul" in the_spell:
                if card_data in the_spell["soul"]:
                    the_spell["soul"].remove(card_data)

        case 'deck':
            deck_list = game_rooms[room_code]['players'][username]['deck_list']
            index = next((i for i, c in enumerate(deck_list) if c['id'] == card_data['id']), None)
            if index is not None:
                deck_list.pop(index)
                game_rooms[room_code]['players'][username]['current_deck_count'] -= 1

        case 'gauge':
            current_gauge = game_rooms[room_code]['players'][username]['current_gauge']
            index = next((i for i, c in enumerate(current_gauge) if c['id'] == card_data['id']), None)
            if index is not None:
                current_gauge.pop(index)
                game_rooms[room_code]['players'][username]['current_gauge_size'] -= 1

        case _:
            pass

def place_card_in_zone(card_data, to_zone, room_code, spell_id=None):
    username = session['user']
    card_data.setdefault('soul', [])
    card_data.setdefault('rest', False)
    if to_zone in ("deck", "hand", "dropzone"):
        if card_data["soul"]:
            for soul_card in card_data["soul"]:
                game_rooms[room_code]['players'][username]["dropzone"].append(soul_card)
            card_data["soul"].clear() 

    match to_zone:
        case _ if to_zone in ("left", "center", "right", "item"):
            occupant = game_rooms[room_code]['players'][username][to_zone]
            if occupant is not None:
                occupant.setdefault('soul', [])
                occupant.setdefault('rest', False)

                card_data["soul"].append(occupant)

                if occupant["soul"]:
                    card_data["soul"].extend(occupant["soul"])
                    occupant["soul"].clear()

            game_rooms[room_code]['players'][username][to_zone] = card_data

        case "hand":
            game_rooms[room_code]['players'][username]['current_hand'].append(card_data)
            game_rooms[room_code]['players'][username]['current_hand_size'] += 1

        case "dropzone":
            game_rooms[room_code]['players'][username]["dropzone"].append(card_data)

        case "spells":
            game_rooms[room_code]['players'][username]["spells"].append(card_data)

        case 'spell-soul':
            spells = game_rooms[room_code]['players'][username]['spells']
            the_spell = next((s for s in spells if s['id'] == spell_id), None)
            if the_spell:
                the_spell.setdefault("soul", [])
                the_spell["soul"].append(card_data)

        case "deck":
            game_rooms[room_code]['players'][username]['deck_list'].append(card_data)
            game_rooms[room_code]['players'][username]['current_deck_count'] += 1

        case "gauge":
            game_rooms[room_code]['players'][username]['current_gauge'].append(card_data)
            game_rooms[room_code]['players'][username]['current_gauge_size'] += 1

        case _:
            pass

def english_checker(from_zone, to_zone, card, username):
    action = 'moves'
    place = f' from the {from_zone} to the {to_zone}'
    if from_zone == 'hand':
        place = f"to the {to_zone}"
        action = 'calls'
        if to_zone == 'dropzone':
            action = 'drops'
            place = ''
        if to_zone == 'deck':
            action = 'returns'
            place = ' to the deck'
        if to_zone == 'item':
            action = 'equips'
            place = ''
            if card['type'] == 'Impact Monster' and to_zone not in ['left', 'center', 'right']:
                action = 'transforms into'
            if card['type'] == 'Monster' and to_zone not in ['left', 'center', 'right']:
                action = 'transforms into'
        if to_zone == 'gauge':
            english = f"{username} charges."
            return english
    
    if from_zone == 'deck':
        if to_zone == 'hand':
            place = ' from deck'
            action = 'searches for'
        if to_zone in ['left', 'center', 'right']:
            place = f" to the {to_zone} from the deck"
            action = 'calls'
        if to_zone == 'dropzone':
            action = 'drops from deck'
        if to_zone == 'item':
            action = 'equips from deck'
            place = ''
            if card['type'] == 'Impact Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into'
            if card['type'] == 'Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into from deck'
    
    if from_zone == 'dropzone':
        if to_zone == 'hand':
            place = ''
            action = 'returns'
        if to_zone in ['left', 'center', 'right']:
            place = f" to the {to_zone} from the dropzone"
            action = 'calls'
        if to_zone == 'deck':
            action = 'returns'
            place = ' from dropzone to deck'
        if to_zone == 'item':
            action = 'equips'
            place = ''
            if card['type'] == 'Impact Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into'
            if card['type'] == 'Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into'
    
    if from_zone in ['left', 'center', 'right', 'item']:
        if to_zone == 'hand':
            place = ' to the hand'
            action = 'returns'
        if to_zone == 'deck':
            action = 'returns'
            place = ' to the bottom of the deck'
        if to_zone == 'dropzone':
            action = 'drops'
            english = f"{card['name']} has been destroyed."
            return english
        if to_zone == 'item':
            action = 'equips'
            place = ''
            if card['type'] == 'Impact Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into'
            if card['type'] == 'Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into'
        if from_zone == 'item':
            place = ''
    
    if to_zone == 'spell':
        action = 'casts'
        place = ''
    
    english = f"{username} {action} {card['name']}{place}."
    return english