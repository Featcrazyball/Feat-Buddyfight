# Importing necessary libraries
from flask import Flask, render_template, request, redirect, url_for, flash, session, get_flashed_messages, send_from_directory, jsonify, abort, session
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms, close_room
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename, redirect
from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified
from threading import Timer
# Personal Libraries
from models import db, Card, User, Report, Deck, Sleeve, PaymentHistory, Item
from error import handle_error
from cardExtractor import *
import os, random, json, string, time, eventlet, uuid

# Initialize Flask app and database
app = Flask(__name__, template_folder='templates', static_folder="static", static_url_path='/')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///default.db'  
app.config['SQLALCHEMY_BINDS'] = {
    'users': 'sqlite:///users.db',
    'cards': 'sqlite:///buddyfight_cards.db',
    'reports': 'sqlite:///reports.db',
    'item': 'sqlite:///items.db',
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 300}
app.secret_key = "supersecretkey"

db.init_app(app)

# Profile Picture
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'profile_images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Sleeves
UPLOAD_SLEEVE = os.path.join('static', 'img', 'sleeves')
app.config['UPLOAD_SLEEVE'] = UPLOAD_SLEEVE

# For chat Rooms and Arena
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*", logger=True, engineio_logger=True)

chat_rooms = {
    "General": {"messages": []},
    "Deck": {"messages": []},
    "Events": {"messages": []}
}  

# Error handling
# app.register_error_handler(Exception, handle_error)

game_rooms = {}
user_rooms = {} 

# Role-based access control decorators for Admin required
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(func):
    @wraps(func) 
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login'))
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
    """Method to deselect the currently selected deck."""
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

def delayed_room_cleanup(room_code):
    try:
        game_room = game_rooms.get(room_code)
        if game_room and not game_room["players"]: 
            del game_rooms[room_code]
            print(f"Room {room_code} deleted due to inactivity.")
    except KeyError:
        print(f"Room {room_code} already handled.")

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

@app.route('/')
def index():
    return redirect(url_for('home'))

# Register [Completed]
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        # Validate input
        if len(username) < 3:
            flash("Username must be at least 3 characters long.", "error")
            return redirect(url_for('register'))

        if len(password) < 8:
            flash("Passwords must be at least 8 characters long.", "error")
            return redirect(url_for('register'))

        if password != confirmation:
            flash("Passwords do not match!", "error")
            return redirect(url_for('register'))

        # Check if username or email already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists! Please login.", "error")
            return redirect(url_for('register'))
        
        existing_email = User.query.filter((User.email == email)).first()
        if existing_email:
            flash("Email already exists! Please login.", "error")
            return redirect(url_for('register'))

        trial_deck_cards = Card.query.filter(
            or_(
                Card.rarity.ilike("TD"),
                Card.rarity.ilike("SD")
            )
        ).all()
        unlocked_cards = [card.id for card in trial_deck_cards]  # Extract card numbers

        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, role='user', unlocked_cards=unlocked_cards)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Login [Completed]
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.username
            session['user_role'] = user.role
            return redirect(url_for('home', usr=user.username))

        flash("Invalid username or password.", "error")
        return redirect(url_for('login'))

    return render_template('login.html')

# Home Page [Incomplete]
@app.route('/home', methods=['GET'])
def home():
    return render_template('home.html')

# Anime [Incomplete]
@app.route('/anime', methods=['GET'])
@login_required
def anime():
    return render_template('anime.html', username=session['user'])

# Card List [Complete]
@app.route('/list', methods=['GET'])
@login_required
def list():
    action = 'delete'
    object = 'card'
    search_query = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    rarity_filter = request.args.get('rarity', '')
    world_filter = request.args.get('world', '')
    size_filter = request.args.get('size', '')
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
    if unlocked_only:
        user = User.query.filter_by(username=session['user']).first()
        if user:
            unlocked_card_ids = user.unlocked_cards
            query = query.filter(Card.id.in_(unlocked_card_ids))

    cards = query.all()
    card_dicts = [card.to_dict() for card in cards]  # Ensure this is serialized as a list of dictionaries
    return render_template('list.html', username=session['user'], cards=card_dicts, search_query=search_query, action=action, object=object)

# Card Extractor for card list
@app.route('/scrape')
@admin_required
def scrape_cards():
    try:
        scrape_all_cards()
        flash("Card data successfully updated!", "success")
    except Exception as e:
        flash(f"Error during scraping: {e}", "danger")
    return redirect(url_for('cards'))

# Route to update an existing card
@app.route('/update_card/<int:card_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('list'))

    return render_template('update_card.html', card=card, action=action, object=object) 

@app.route('/delete_card/<int:card_id>', methods=['POST'])
@admin_required
def delete_card(card_id):
    card = Card.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    flash("Card deleted successfully!", "success")
    return redirect(url_for('list'))

# Shops [Incomplete]
@app.route('/shops', methods=['GET', 'POST'])
@login_required
def shop():
    items = Item.query.all()
    return render_template('shops.html', username=session['user'], items=items)

@app.route('/shops/make_payment', methods=['POST'])
@login_required
def make_payment():
    item_id = request.form.get('item_id')
    item_price = request.form.get('item_price')
    card_number = request.form.get('card_number')
    expiration_date = request.form.get('expiration_date')
    cvv = request.form.get('cvv')

    item = Item.query.filter_by(id=item_id).first()
    user = User.query.filter_by(username=session['user']).first()

    app.logger.info(f"Item ID: {item_id}, Item Price: {item_price}, Card: {card_number}, Expiry: {expiration_date}, CVV: {cvv}")

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
        app.logger.error(f"Error processing payment: {e}")
        return jsonify({"status": "error", "message": 'Failed to process payment'}), 500

@app.route('/shops/manual', methods=['GET','POST'])
def add_shops():
    items_to_add = [
        {"count": 1, "price": 2.50},
        {"count": 3, "price": 6.00},
        {"count": 10, "price": 17.50},
        {"count": 30, "price": 50.00},
        {"count": 100, "price": 150.00},
        {"count": 1000, "price": 1000.00}
    ]

    for item_data in items_to_add:
        existing_item = Item.query.filter_by(count=item_data['count']).first()
        if not existing_item:
            new_item = Item(count=item_data['count'], price=item_data['price'])
            db.session.add(new_item)

    try:
        db.session.commit()
        return jsonify({"message": "Items added successfully!"}), 200
    except Exception as e:
        app.logger.error(f"Error seeding item: {e}")
        return jsonify({"error": "Failed to add items", "message": str(e)}), 500
    
# Chat Rooms [Completed]
@app.route('/chat', methods=['GET'])
@login_required
def chat():
    return render_template('chatrooms.html', username=session.get('user', 'Anonymous'))

@app.route('/create_room', methods=['POST'])
@login_required
def create_room():
    raw_code = str(uuid.uuid4()).replace('-', '').upper()
    first_letter = random.choice(string.ascii_uppercase)
    room_code = first_letter + raw_code[:7]
    chat_rooms[room_code] = {"messages": []}
    return jsonify({"room_code": room_code})

@app.route('/join_room', methods=['POST'])
@login_required
def join_room_http():
    data = request.json
    room_code = data.get('room_code')
    if not room_code or room_code not in chat_rooms:
        return jsonify({"error": "Room not found"}), 404
    return jsonify({"status": "success"})

@socketio.on('connect')
@login_required
def handle_connect():
    print("Socket connected, SID:", request.sid)

@socketio.on('join_room')
@login_required
def on_join_room(data):
    room = data.get('room')
    username = session.get('user')

    join_room(room)
    print(f"{username} is joining {room}")

    if room not in ['Events', 'Deck', 'General']:
        msg = f"{username} joined the room."
        add_message_to_room(room, "System", msg)
        emit('receive_message', {
            "room": room, 
            "message": msg, 
            "username": "System"
        }, room=room)

    history = chat_rooms[room]["messages"][-500:]
    emit('room_history', history, room=request.sid)

@socketio.on('leave_room')
@login_required
def on_leave_room(data):
    room = data.get('room')
    username = session.get('user')

    leave_room(room)
    print(f"{username} left {room}")

    msg = f"{username} left the room."
    add_message_to_room(room, "System", msg)
    emit('receive_message', {
        "room": room,
        "message": msg,
        "username": "System"
    }, room=room)

@socketio.on('send_message')
@login_required
def on_send_message(data):
    room = data.get('room')
    message = data.get('message')
    username = session.get('user')

    if room == "Events":
        user = User.query.filter_by(username=username).first()
        if user.role != 'admin':
            emit('chat_error', {
                "message": "Only admins can chat in Events."
            }, room=request.sid)
            return

    add_message_to_room(room, username, message)

    emit('receive_message', {
        "room": room,
        "message": message,
        "username": username
    }, room=room)

# Arena HOME PAGE [COMPLETED]
@app.route('/arenaHome', methods=['GET', 'POST'])
@login_required
def arenaHome():
    return render_template('arenaHome.html', username=session['user'])

# Arena LOBBY PAGE ONLY [DO NOT DO ANYTHING] [Completed]
@app.route('/arenaLobby', methods=['GET', 'POST'])
@login_required
def arenaLobby():
    user = User.query.filter_by(username=session['user']).first()
    selected_deck = None
    if user.selected_deck_id:
        deck = Deck.query.get(user.selected_deck_id)
        if deck:
            selected_deck = deck.name

    return render_template('arenaLobby.html', username=session['user'], selected_deck=selected_deck)

@app.route('/active_game_rooms', methods=['GET'])
def get_active_game_rooms():
    active_rooms = get_active_game_rooms_list()
    return jsonify(active_rooms)

@socketio.on("get_active_game_rooms")
def socket_active_game_rooms():
    active_rooms = [
        {
            "room_code": room,
            "creator_username": game_rooms[room]["creator_username"],
            "creator_profile_picture": game_rooms[room]["creator_profile_picture"],
        }
        for room in game_rooms
    ]
    emit("active_game_rooms", active_rooms)

@socketio.on("create_game_room")
@login_required
def create_game_room():
    user = User.query.filter_by(username=session['user']).first()
    user_deck = Deck.query.get(user.selected_deck_id)
    profile_picture = user.profile_image
    username = user.username

    if username in user_rooms:
        emit('error', {"message": "You are already in a room.", "status": "error"}, room=request.sid)
        return

    if user.selected_deck_id is None:
        emit('error', {"message": "Please select a deck first.", "status": "error"}, room=request.sid)
        return
    
    if user_deck.buddy_card_id is None:
        emit('error', {"message": "Please select a buddy card first.", "status": "error"}, room=request.sid)
        return

    if user.profile_image == "uploads/default_profile.jpg":
        profile_picture = "default_profile.jpg"

    room_code = generate_room_code()
    game_rooms[room_code] = {
        "creator_username": username,
        "creator_profile_picture": f"/uploads/{profile_picture}",
        "players": {username: {}},
        "game_state": {},
    }

    user_rooms[username] = room_code
    join_room(room_code)

    socketio.emit('update_active_game_rooms', get_active_game_rooms_list())
    emit('game_room_created', {
        "status": "success",
        "room_code": room_code,
    }, room=request.sid)

@socketio.on('join_game_room')
@login_required
def join_game_room(data):
    room_code = data.get('room')
    username = session.get('user')

    user = User.query.filter_by(username=username).first()
    user_deck = Deck.query.filter_by(id=user.selected_deck_id).first()

    if username in user_rooms:
        emit('error', {"message": "You are already in a room.", "status": "error"}, room=request.sid)
        return

    if user.selected_deck_id is None:
        emit('error', {"message": "Please select a deck first.", "status": "error"}, room=request.sid)
        return
    
    if user_deck.buddy_card_id is None:
        emit('error', {"message": "Please select a buddy card first.", "status": "error"}, room=request.sid)
        return

    if room_code not in game_rooms:
        emit('error', {"message": "Room does not exist.", "status": "error"}, room=request.sid)
        return

    if len(game_rooms[room_code]["players"].keys()) >= 2:
        emit('error', {"message": "Room is full.", "status": "error"}, room=request.sid)
        return

    join_room(room_code)
    game_rooms[room_code]["players"][username] = {}
    user_rooms[username] = room_code

    print(f"{username} joined room {room_code}. Current players: {game_rooms[room_code]['players']}")
    socketio.emit('update_active_game_rooms', get_active_game_rooms_list())

    opponent = opponent_checker(room_code, username)
    room_data = game_rooms[room_code]
    # Decks
    player_opponent = User.query.filter_by(username=opponent).first()
    opponent_deck = Deck.query.filter_by(id=player_opponent.selected_deck_id).first()

    # Link to card model
    user_deck_card_ids = user_deck.cards     
    opponent_deck_card_ids = opponent_deck.cards 

    # Shuffling Deck
    user_deck_card_ids = shuffle_deck(user_deck_card_ids)
    opponent_deck_card_ids = shuffle_deck(opponent_deck_card_ids)

    # Getting Hand and gauge
    user_hand_ids, user_remaining_deck = draw_cards(user_deck_card_ids, user_deck.initial_hand_size)
    user_gauge_ids, user_remaining_deck = draw_cards(user_remaining_deck, user_deck.initial_gauge)

    opponent_hand_ids, opponent_remaining_deck = draw_cards(opponent_deck_card_ids, opponent_deck.initial_hand_size)
    opponent_gauge_ids, opponent_remaining_deck = draw_cards(opponent_remaining_deck, opponent_deck.initial_gauge)

    # Get card data
    user_hand = get_card_data(user_hand_ids)
    user_gauge = get_card_data(user_gauge_ids)

    opponent_hand = get_card_data(opponent_hand_ids)
    opponent_gauge = get_card_data(opponent_gauge_ids)

    user_deck_list = get_card_data(user_remaining_deck)
    opponent_deck_list = get_card_data(opponent_remaining_deck)

    # Deck Count
    user_deck_count = len(user_remaining_deck)
    opponent_deck_count = len(opponent_remaining_deck)

    game_rooms[room_code]['players'][username] = {
            'current_life': user_deck.initial_life,
            'current_gauge_size': user_deck.initial_gauge,
            'current_gauge': user_gauge,
            'current_hand_size': user_deck.initial_hand_size,
            'current_hand': user_hand,
            'deck_list': user_deck_list,
            'current_deck_count': user_deck_count,
            'left': None,
            'center': None,
            'right': None,
            'item': None,
            'spells': [],
            'dropzone': [],
            'buddy_rest': False,
            'selector': None,
            'current_phase': 'Draw Phase',
            'highlighter': None
        }

    game_rooms[room_code]['players'][opponent] = {
        'current_life': opponent_deck.initial_life,
        'current_gauge_size': opponent_deck.initial_gauge,
        'current_gauge': opponent_gauge,
        'current_hand_size': opponent_deck.initial_hand_size,
        'current_hand': opponent_hand,
        'deck_list': opponent_deck_list,
        'current_deck_count': opponent_deck_count,
        'left': None,
        'center': None,
        'right': None,
        'item': None,
        'spells': [],
        'dropzone': [],
        'buddy_rest': False,
        'selector': None,
        'current_phase': 'End Turn',
        'highlighter': None
    }

    if len(room_data["players"]) == 2:
        eventlet.sleep(0.5)
        emit('joining_game_player', {
            'opponent': opponent
        }, room=request.sid)

        emit('room_creator_player', {
            'opponent': username
        }, room=room_code, include_self=False)

        emit('room_ready', {
            "message": f"Room {room_code} is ready!",
            "room_code": room_code,
            "redirect_url": url_for('gameplay', room_code=room_code),
        }, room=room_code)

@socketio.on('leave_created_game_room')
def leave_created_game_room(data):
    room_code = data.get('room')
    username = session['user']

    if room_code not in game_rooms:
        emit('error', {"message": "Invalid or non-existent room.", "status": "error"}, room=request.sid)
        return

    players = game_rooms[room_code]["players"]
    if username in players:
        del players[username]
        leave_room(room_code)

        if username in user_rooms:
            del user_rooms[username]

        if len(players) == 1:
            remaining_user = next(iter(players.keys()), None)
            socketio.emit('game_end', {
                "message": f"Game End. Winner: {remaining_user}",
                "room_code": room_code,
                "redirect_url": url_for('arenaLobby'),
            }, room=room_code)
            if remaining_user in user_rooms:
                del user_rooms[remaining_user]
            del game_rooms[room_code]

        elif len(players) == 0:
            del game_rooms[room_code]

        socketio.emit('update_active_game_rooms', get_active_game_rooms_list())

        emit('room_closed', {
            "message": "You have left the room.",
            "redirect_url": url_for('arenaLobby'),
        }, room=request.sid)

    else:
        emit('error', {"message": "You are not in that room.", "status": "error"}, room=request.sid)

@app.route('/gameplay/<room_code>')
@login_required
def gameplay(room_code):
    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        flash("User not found", "error")
        return redirect(url_for("arenaLobby"))

    game_room = game_rooms.get(room_code)
    if not game_room or current_user.username not in game_room["players"]:
        flash("Invalid game room or you are not in this room", "error")
        return redirect(url_for("arenaLobby"))

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

@app.route('/gameplay/gameInitialisation/<room_code>', methods=['POST'])
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

@app.route("/gameplay/gameInformation/<room_code>", methods=['POST'])
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

@socketio.on('game_room_joined')
def game_room_joined(data):
    room_code = data.get('room')
    join_room(room_code)
    return

# Phase Updater [Complete]
@socketio.on('phase_update')
def phase_update(data):
    room_code = data.get('room')
    phase = data.get('phase')
    username = session['user']

    game_rooms[room_code]['players'][username]['current_phase'] = data.get('phase')

    emit('phase_updated', {
        'phase': phase
    }, room=room_code, include_self=False)

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has entered the {phase} phase."
        }, room=room_code)

# Life Counter [Complete]
@socketio.on('life_increase')
def life_increase(data):
    room_code = data.get('room')
    username = session['user']
    game_rooms[room_code]['players'][username]['current_life'] += 1
    current_life = game_rooms[room_code]['players'][username]['current_life']
    emit('life_update', {'current_life': current_life}, room=room_code, include_self=False)

@socketio.on('life_decrease')
def life_decrease(data):
    room_code = data.get('room')
    username = session['user']
    game_rooms[room_code]['players'][username]['current_life'] -= 1
    current_life = game_rooms[room_code]['players'][username]['current_life']
    emit('life_update', {'current_life': current_life}, room=room_code, include_self=False)

# Card Draw [Complete]
@socketio.on('draw_card')
def draw_card(data):
    room_code = data.get('room')
    cards_drawn = data.get('cards_drawn')
    username = session['user']
    deck = game_rooms[room_code]['players'][username]['deck_list']

    if (game_rooms[room_code]['players'][username]['current_deck_count']) - cards_drawn < 0:
        emit('mini_modal', {
            'sender': 'System',
            'status': 'error',
            'message': "Not Enough Cards in Deck"
        }, room=request.sid)
        return

    drawn_cards, remaining_deck = draw_cards(deck, cards_drawn)
    game_rooms[room_code]['players'][username]['deck_list'] = remaining_deck
    game_rooms[room_code]['players'][username]['current_deck_count'] = len(remaining_deck)
    game_rooms[room_code]['players'][username]['current_hand_size'] += cards_drawn
    game_rooms[room_code]['players'][username]['current_hand'].extend(drawn_cards)

    english_checker = 'card' if cards_drawn == 1 else 'cards'
    english_checker_2 = 'a' if cards_drawn == 1 else cards_drawn

    emit('card_drawn', {
        'hand': game_rooms[room_code]['players'][username]['current_hand'],
        'hand_size': game_rooms[room_code]['players'][username]['current_hand_size'],
        'deck_count': len(remaining_deck),
        'cards_drawn': cards_drawn
    }, room=room_code, include_self=False)

    emit('update_game_information', {}, room=request.sid)

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has drawn {english_checker_2} {english_checker}."
        }, room=room_code)

# Gauge Update [Complete]
@socketio.on('gauge_update')
def gauge_update(data):
    room_code = data.get('room')
    gauge_change = data.get('gauge_change')
    username = session['user']

    current_gauge = game_rooms[room_code]['players'][username]['current_gauge_size']

    if current_gauge + gauge_change < 0:
        emit('mini_modal', {
            'sender': 'System',
            'status': 'error',
            'message': f"{username} does not have enough gauge to pay."
        }, room=request.sid)
        return
    
    if (game_rooms[room_code]['players'][username]['current_deck_count']) - gauge_change < 0:
        emit('mini_modal', {
            'sender': 'System',
            'status': 'error',
            'message': "Not Enough Cards in Deck"
        }, room=request.sid)
        return

    deck = game_rooms[room_code]['players'][username]['deck_list']

    if gauge_change > 0:
        gauge_cards, remaining_deck = draw_cards(deck, gauge_change)
        game_rooms[room_code]['players'][username]['deck_list'] = remaining_deck
        game_rooms[room_code]['players'][username]['current_deck_count'] = len(remaining_deck)
        game_rooms[room_code]['players'][username]['current_gauge'].extend(gauge_cards)
        game_rooms[room_code]['players'][username]['current_gauge_size'] += gauge_change

        emit('update_game_information', {}, room=room_code)

    if gauge_change < 0:
        for _ in range(abs(gauge_change)):
            gauge_taken_away = game_rooms[room_code]['players'][username]['current_gauge'][-1]
            game_rooms[room_code]['players'][username]['current_gauge'].pop()
            game_rooms[room_code]['players'][username]['dropzone'].append(gauge_taken_away)
            game_rooms[room_code]['players'][username]['current_gauge_size'] -= 1

            emit('update_game_information', {}, room=room_code)
            eventlet.sleep(0.1)

    english_checker = 'gained' if gauge_change > 0 else 'paid'

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has {english_checker} {abs(gauge_change)} gauge."
        }, room=room_code)

# Card call [Complete]
@socketio.on('card_move')
def card_moved(data):
    room_code = data.get("room")
    username = session['user']
    card_data = data.get("card")
    from_zone = data.get("from_zone")
    to_zone = data.get("to_zone")
    spell_id = data.get("spell_id")  

    remove_card_from_zone(card_data, from_zone, room_code, spell_id)
    place_card_in_zone(card_data, to_zone, room_code, spell_id)

    emit('update_game_information', {}, room=room_code)

    emit('mini_chat_message', {
        'sender': 'System',
        'message': english_checker(from_zone, to_zone, card_data, username)
    }, room=room_code)

def remove_card_from_zone(card_data, from_zone, room_code, spell_id=None):
    username = session['user']

    match from_zone:
        case _ if from_zone in ("left", "center", "right", "item"):
            occupant = game_rooms[room_code]['players'][username][from_zone]
            if occupant and occupant['id'] == card_data['id']:
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
            engerish = f"{username} charges."
            return engerish
    
    if from_zone == 'deck':
        if to_zone == 'hand':
            place = ''
            action = 'searches for'
        if to_zone in ['left', 'center', 'right']:
            place = f"to the {to_zone}"
            action = 'calls'
        if to_zone == 'dropzone':
            action = 'drops'
        if to_zone == 'item':
            action = 'equips'
            place = ''
            if card['type'] == 'Impact Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into'
            if card['type'] == 'Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into'
    
    if from_zone == 'dropzone':
        if to_zone == 'hand':
            place = ''
            action = 'returns'
        if to_zone in ['left', 'center', 'right']:
            place = f"to the {to_zone} from the dropzone"
            action = 'calls'
        if to_zone == 'deck':
            action = 'returns'
        if to_zone == 'item':
            action = 'equips'
            place = ''
            if card['type'] == 'Impact Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into'
            if card['type'] == 'Monster' and to_zone not in ['left', 'center', 'right', 'item']:
                action = 'transforms into'

    if from_zone in ['left', 'center', 'right', 'item']:
        if to_zone == 'hand':
            place = 'to the hand'
            action = 'returns'
        if to_zone == 'deck':
            action = 'returns'
            place = ' to the bottom of the deck'
        if to_zone == 'dropzone':
            action = 'drops'
            engerish = f"{card['name']} has been destroyed."
            return engerish
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

    engerish = f"{username} {action} {card['name']}{place}."
    return engerish

@socketio.on("highlight_card")
def handle_highlight_card(data):
    room_code = data["room"]
    username = session["user"]
    card_data = data["card"]

    if game_rooms[room_code]['players'][username].get('highlighter'):
        current_highlight = game_rooms[room_code]['players'][username].get('highlighter')
        if current_highlight == card_data["id"]:
            game_rooms[room_code]['players'][username]['highlighter'] = None
        else:
            game_rooms[room_code]['players'][username]['highlighter'] = card_data["id"]

    emit("update_game_information", {}, room=room_code)

@socketio.on("card_rest_toggle")
def handle_card_rest_toggle(data):
    room_code = data["room"]
    username = session["user"]
    card_data = data["card"]
    zone = data.get('zone')

    game_rooms[room_code]['players'][username][zone]['rest'] = not game_rooms[room_code]['players'][username][zone]['rest']

    if card_data["rest"] == True:
        if game_rooms[room_code]['players'][username]['current_phase'] == "Attack Phase":
            action = 'attacks'
        else:
            action = 'rests'
    else:
        action = 'stands'

    emit("update_game_information", {}, room=room_code)

    emit("mini_chat_message", {
        "sender": "System",
        "message": f"{card_data['name']} {action}."
        }, room=room_code)

@socketio.on("buddy_call")
def buddy_call(data):
    room_code = data["room"]
    username = session["user"]

    if game_rooms[room_code]["players"][username]["buddy_rest"] == True:
        game_rooms[room_code]['players'][username]['buddy_rest'] = False
        emit("mini_chat_message", {
            "sender": "System",
            "message": f"{username} is cheating."
        }, room=room_code)
    elif game_rooms[room_code]["players"][username]["buddy_rest"] == False:
        game_rooms[room_code]['players'][username]['buddy_rest'] = True
        emit("mini_chat_message", {
            "sender": "System",
            "message": f"{username} Buddycalls."
        }, room=room_code)

    emit("update_game_information", {}, room=room_code)

# Search Deck [Complete]
@socketio.on('search_deck')
def card_call_soul(data):
    room_code = data.get('room')
    card = data.get('card')
    username = session['user']

    game_rooms[room_code]['players'][username]['deck_list'].remove(card)
    game_rooms[room_code]['players'][username]['current_deck_count'] -= 1
    game_rooms[room_code]['players'][username]['current_hand'].append(card)
    game_rooms[room_code]['players'][username]['current_hand_size'] += 1

    emit('update_game_information', {}, room=room_code)

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} adds {card.name} from the deck to hand."
        }, room=room_code)

@socketio.on('search_deck_open')
def search_open(data):
    room_code = data.get('room')
    username = session['user']

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has opened the deck."
        }, room=room_code)
    
    emit('update_game_information', {}, room=request.sid)

@socketio.on('search_deck_close')
def search_close(data):
    room_code = data.get('room')
    username = session['user']

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has closed the deck."
        }, room=room_code)
    
    emit('update_game_information', {}, room=request.sid)

# Search Dropzone [Complete]
@socketio.on('search_dropzone')
def search_dropzone(data):
    room_code = data.get('room')
    card = data.get('card')
    username = session['user']

    game_rooms[room_code]['players'][username]['dropzone'].remove(card)
    game_rooms[room_code]['players'][username]['current_hand'].append(card)
    game_rooms[room_code]['players'][username]['current_hand_size'] += 1

    emit('update_game_information', {}, room=room_code, include_self=False)

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} adds {card.name} from his dropzone to his hand."
        }, room=room_code)

@socketio.on('search_dropzone_open')
def search_dropzone_open(data):
    room_code = data.get('room')
    username = session['user']

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has opened the dropzone."
        }, room=room_code)
    
@socketio.on('search_dropzone_close')
def search_dropzone_close(data):
    room_code = data.get('room')
    username = session['user']

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has closed the dropzone."
        }, room=room_code)
    
@socketio.on('search_opponent_dropzone_open')
def search_opponent_dropzone_open(data):
    room_code = data.get('room')
    username = session['user']

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has opened the opponent's dropzone."
        }, room=room_code)
    
@socketio.on('search_opponent_dropzone_close')
def search_opponent_dropzone_close(data):
    room_code = data.get('room')
    username = session['user']

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has closed the opponent's dropzone."
        }, room=room_code)

# Shuffle Deck [Complete]
@socketio.on('shuffle_deck')
def handle_shuffle_deck(data):
    room_code = data.get('room')
    username = session['user']

    deck = game_rooms[room_code]['players'][username]['deck_list']
    deck = shuffle_deck(deck)
    game_rooms[room_code]['players'][username]['deck_list'] = deck

    emit('update_game_information', {}, room=room_code)

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{username} has shuffled the deck."
        }, room=room_code)

# Drop Top Deck to Dropzone [Complete]
@socketio.on('top_deck_to_dropzone')
def top_deck_to_dropzone(data):
    room_code = data.get('room')
    number_of_cards = data.get('number_of_cards')
    username = session['user']

    deck = game_rooms[room_code]['players'][username]['deck_list']
    game_rooms[room_code]['players'][username]['deck_list'] = deck[number_of_cards:]
    for _ in range(number_of_cards):
        card = deck.pop(0)
        game_rooms[room_code]['players'][username]['dropzone'].append(card)
    game_rooms[room_code]['players'][username]['deck_list'] = deck
    game_rooms[room_code]['players'][username]['current_deck_count'] -= number_of_cards

    emit('dropzone_from_deck', {
        'deck_count': game_rooms[room_code]['players'][username]['current_deck_count'],
        'deck': game_rooms[room_code]['players'][username]['deck_list'],
        'dropzone': game_rooms[room_code]['players'][username]['dropzone'],
    }, room=room_code, include_self=False)

    emit('update_game_information', {}, room=request.sid)

    emit('mini_chat_message', {
        'sender': 'System',
        'message': f"{card.name} has been dropped from the top of the deck."
        }, room=room_code)

# Mini Chat [Complete]
@socketio.on("mini_chat_send")
@login_required
def mini_chat_send(data):
    room_code = data.get("room")
    message = data.get("message")
    sender = session['user']
    emit("mini_chat_message", {
        "sender": sender,
        "message": message
    }, room=room_code)

# Game End [Complete]
@socketio.on("game_end")
@login_required
def handle_game_end(data):
    room_code = data.get("room")
    winner = data.get("winner")
    emit("game_end", {
        'message': f"Game End. Winner: {winner}",
        "winner": winner
    }, room=room_code)

# Sleeves [Completed]
@app.route('/sleeves', methods=['GET', 'POST'])
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

@app.route('/select_sleeve/<int:sleeve_id>', methods=['POST'])
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
@app.route('/deckBuilder', methods=['GET'])
@login_required 
def deck_builder():
    decks = Deck.query.filter_by(username=session['user']).all()
    deck_dicts = [deck.to_dict() for deck in decks]

    selected_deck_id = next((deck.id for deck in decks if deck.selected), None)

    return render_template('deckBuilder.html', username=session['user'], decks=deck_dicts, selected_deck_id=selected_deck_id)

@app.route('/deckBuilder/create_deck', methods=['POST'])
@login_required
def create_deck():
    username = session['user']
    deckName = request.form.get('name', '')
    flag = request.form.get('flag', '')

    if not deckName or not flag:
        return jsonify({"status": "error", "message": "Both name and flag are required."}), 400

    if Deck.query.filter_by(username=username).count() >= 4:
        return jsonify({"status": "error", "message": "You can only have up to 4 decks."}), 400

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
        case _:
            flagImg = 'img/CardBack.webp'  # Default image

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

    # Create the new deck
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
        app.logger.error(f"Create deck error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success", "message": f"Deck '{deckName}' created successfully!"})

@app.route('/select_deck/<int:deck_id>', methods=['POST'])
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

@app.route('/deckBuilder/delete_deck/<int:deck_id>', methods=['POST'])
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
        app.logger.error(f"Failed to delete deck: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while deleting the deck."}), 500

@app.route('/edit_deck', methods=['GET'])
def edit_deck(): 
    user = User.query.filter_by(username=session['user']).first()
    if not user or not user.selected_deck_id:
        flash("No deck selected. Please select a deck first.", "error")
        return redirect(url_for('deck_builder'))

    selected_deck = Deck.query.get(user.selected_deck_id)
    if not selected_deck:
        flash("Selected deck not found.", "error")
        return redirect(url_for('deck_builder'))

    valid_flags = ["Generic"]
    valid_attributes = []
    exclude_types = []

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
        case 'Searing Executioners':
            valid_attributes.append("Executioners")
        case _:
            valid_flags.append(selected_deck.flag)

    unlocked_cards_query = Card.query.filter(Card.id.in_(user.unlocked_cards))
    
    # Filter by valid flags and attributes
    attribute_filters = [Card.attribute.ilike(f"%{attr}%") for attr in valid_attributes]
    unlocked_cards_query = unlocked_cards_query.filter(
        (Card.world.in_(valid_flags)) | or_(*attribute_filters)
    )

    # Exclude specific types
    if exclude_types:
        unlocked_cards_query = unlocked_cards_query.filter(~Card.type.in_(exclude_types))

    # Search query
    search_query = request.args.get('name', '').strip()
    if search_query:
        unlocked_cards_query = unlocked_cards_query.filter(Card.name.ilike(f"%{search_query}%"))

    unlocked_cards = unlocked_cards_query.all()

    return render_template('edit_deck.html', deck=selected_deck, unlocked_cards=unlocked_cards, search_query=search_query)

@app.route('/edit_deck/get_deck', methods=['GET'])
@login_required
def get_deck(): 
    user = User.query.filter_by(username=session['user']).first()
    if not user or not user.selected_deck_id:
        return jsonify({"status": "error", "message": "No deck selected"}), 400

    selected_deck = Deck.query.get(user.selected_deck_id)
    if not selected_deck:
        return jsonify({"status": "error", "message": "Deck not found"}), 404

    valid_flags = ["Generic"]
    valid_attributes = []
    exclude_types = []

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
        case 'Searing Executioners':
            valid_attributes.append("Executioners")
        case _:
            valid_flags.append(selected_deck.flag)

    unlocked_cards_query = Card.query.filter(Card.id.in_(user.unlocked_cards))

    attribute_filters = [Card.attribute.ilike(f"%{attr}%") for attr in valid_attributes]
    unlocked_cards_query = unlocked_cards_query.filter(
        (Card.world.in_(valid_flags)) | or_(*attribute_filters)
    )

    if exclude_types:
        unlocked_cards_query = unlocked_cards_query.filter(~Card.type.in_(exclude_types))

    search_query = request.args.get('name', '').strip()
    if search_query:
        unlocked_cards_query = unlocked_cards_query.filter(Card.name.ilike(f"%{search_query}%"))

    unlocked_cards = unlocked_cards_query.all()

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

    unlocked_cards_data = [card.to_dict() for card in unlocked_cards]

    return jsonify({
        "deck": selected_deck_data,
        "unlocked_cards": unlocked_cards_data
    })

@app.route('/edit_deck/save', methods=['POST'])
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
@app.route('/gacha', methods=['GET', 'POST'])
@login_required
def gacha():
    return render_template('gacha.html', username=session['user'])

@app.route('/gacha/tickets', methods=['GET'])
@login_required
def get_ticket_count():
    user = User.query.filter_by(username=session['user']).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    return jsonify({"status": "success", "tickets": user.tickets})

@app.route('/gacha/pull', methods=['POST'])
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
            ~Card.attribute.in_(["SEC", "SECRET", "BR", "SP"]),
            ~Card.image_url.in_(excluded_urls)
        ).all()
    else:
        available_cards = Card.query.filter(
            Card.world.ilike(selected_world),
            ~Card.attribute.in_(["SEC", "SECRET", "BR", "SP"]),
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
@app.route('/about', methods=['GET', 'POST'])
@login_required
def about():
    return render_template('about.html', username=session['user'])

# Settings [Incomplete]
@app.route('/settings', methods=['GET', 'POST'])
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
                "price": payment.item_price,
                "date": payment.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            }
        payment_data.append(payment_detail)

    return render_template(
        'settings.html',
        username=username,
        email=email,
        payments=payment_data
    )

@app.route('/update_username', methods=['POST'])
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
    session['user'] = new_username
    db.session.commit()
    
    db.session.commit()

    return jsonify({"status": "success", "message": "Username updated successfully!"})

@app.route('/update_email', methods=['POST'])
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

@app.route('/update_password', methods=['POST'])
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

@app.route('/delete_user', methods=['POST'])
def delete_user():
    user = User.query.filter_by(username=session['user']).first()

    if user:
        Deck.query.filter_by(username=user.username).delete()
        PaymentHistory.query.filter_by(username=user.username).delete()
        db.session.delete(user)
        db.session.commit()

        session.clear()
        flash("Account has been successfully deleted.")
        return redirect(url_for('login'))

    return jsonify({"status": "error", "message": "User not found. Unable to delete account."}), 500

@app.route('/user_report', methods=['POST'])
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

@app.route('/update_profile_picture', methods=['POST'])
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
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], username.profile_image.split('/')[-1])
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
@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin():
    # For User Filtering
    search_query = request.args.get('search', '')
    query = User.query
    if search_query:
        query = query.filter(
            User.username.ilike(f"%{search_query}%") |
            User.email.ilike(f"%{search_query}%")
        )
    users = query.all()

    # For Report Filtering
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

    sleeves_query = Sleeve.query

    sleeve_search = request.args.get('search_sleeve')
    if sleeve_search:
        sleeves_query = sleeves_query.filter(Sleeve.sleeve_type.ilike(f"%{sleeve_search}%"))

    sleeves = sleeves_query.all()

    return render_template(
        'admin.html',
        username=session['user'],
        users=users,
        search_query=search_query,
        user_reporting_filter = user_reporting_filter,
        reported_user_filter=reported_user_filter,
        report_type_filter=report_type_filter,
        reports=reports,
        sleeves = sleeves
    )

@app.route('/admin/get_users', methods=['GET'])
@admin_required
def get_users():
    search_query = request.args.get('search', '')
    query = User.query
    if search_query:
        query = query.filter(
            User.username.ilike(f"%{search_query}%") |
            User.email.ilike(f"%{search_query}%")
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

@app.route('/admin/get_reports', methods=['GET'])
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

@app.route('/admin/get_sleeves', methods=['GET'])
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

@app.route('/admin/delete_report/<id>', methods=['DELETE'])
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

@app.route('/admin/update_user', methods=['POST'])
@admin_required
def update_user():
    try:
        data = request.form
        username = data.get('username')

        if not username:
            return jsonify({"status": "error", "message": "Username is required"}), 400

        user = User.query.filter_by(username=username).first()

        if user.role == 'admin':
            return jsonify({'status':'error', 'message':'Unaurthorised action.'})

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
        app.logger.error(f"Update user error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/admin/delete_account/<username>', methods=['POST'])
@admin_required
def delete_account(username):
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    if user.role == "admin":
        return jsonify({"status": "error", "message": "Unable to delete admins"})

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
        app.logger.error(f"Failed to delete user: {e}")
        return jsonify({"status": "error", "message": f"Failed to delete user: {str(e)}"}), 500

@app.route('/admin/sleeves', methods=['GET', 'POST'])
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
            filepath = os.path.join(app.config['UPLOAD_SLEEVE'], new_filename)
            file.save(filepath)

            new_sleeve = Sleeve(sleeve=f"img/sleeves/{new_filename}", sleeve_type=sleeve_type)
            db.session.add(new_sleeve)
            db.session.commit()

            return jsonify({"message": "Sleeve added successfully!", "sleeve": new_sleeve.to_dict()})

        return jsonify({"error": "Invalid data"}), 400

@app.route('/testingsleeve')
@admin_required
def delete_all_sleeves():
    try:
        for sleeve in Sleeve.query.all():
            db.session.delete(sleeve)
        db.session.commit()
        return jsonify({"status": "success", "message": "All sleeves deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to delete all sleeves: {e}")
        return jsonify({"status": "error", "message": "An error occurred while deleting all sleeves."}), 500

@app.route('/admin/sleeves/manualCardback')
@admin_required
def add_cardback():
    def seed_sleeves():
        default_sleeves = [
            'img/sleeves/1CardBack.webp',
            'img/sleeves/2CardBack.webp',
            'img/sleeves/3CardBack.webp',
            'img/sleeves/4CardBack.webp',
            'img/sleeves/5CardBack.jpg',
            'img/sleeves/6CardBack.webp',
            'img/sleeves/7CardBack.webp',
            'img/sleeves/8CardBack.webp',
            'img/sleeves/9CardBack.webp',
        ]

        for sleeve_path in default_sleeves:
            if not Sleeve.query.filter_by(sleeve=sleeve_path).first():
                db.session.add(Sleeve(sleeve=sleeve_path, sleeve_type='Buddyfight'))

        db.session.commit()
        print("Default sleeves added to the database.")

    try:
        with app.app_context(): 
            seed_sleeves()
        return jsonify({"message": "Sleeves added successfully!"}), 200
    except Exception as e:
        app.logger.error(f"Error seeding sleeves: {e}")
        return jsonify({"error": "Failed to add sleeves", "message": str(e)}), 500

@app.route('/admin/sleeves/manualVanguard')
@admin_required
def add_sleeves():
    def seed_sleeves():
        default_sleeves = [
            'img/sleeves/_Sleeve51.png',
            'img/sleeves/_Sleeve52.jpg',
            'img/sleeves/_Sleeve53.jpg',
            'img/sleeves/_Sleeve54.webp',
            'img/sleeves/_Sleeve55.webp',
            'img/sleeves/_Sleeve56.webp',
            'img/sleeves/_Sleeve57.webp',
            'img/sleeves/_Sleeve58.webp',
            'img/sleeves/_Sleeve68',
            'img/sleeves/_Sleeve69',
        ]

        for sleeve_path in default_sleeves:
            if not Sleeve.query.filter_by(sleeve=sleeve_path).first():
                db.session.add(Sleeve(sleeve=sleeve_path, sleeve_type='Vanguard'))

        db.session.commit()
        print("Default sleeves added to the database.")
    

    try:
        with app.app_context(): 
            seed_sleeves()
        return jsonify({"message": "Sleeves added successfully!"}), 200
    except Exception as e:
        app.logger.error(f"Error seeding sleeves: {e}")
        return jsonify({"error": "Failed to add sleeves", "message": str(e)}), 500

@app.route('/admin/sleeves/manualSleeves')
@admin_required
def add_sleevesBuddy():
    def seed_sleeves():
        default_sleeves = [
            'img/sleeves/_Sleeve (1).webp',
            'img/sleeves/_Sleeve (2).webp',
            'img/sleeves/_Sleeve (3).webp',
            'img/sleeves/_Sleeve (4).webp',
            'img/sleeves/_Sleeve (5).webp',
            'img/sleeves/_Sleeve (6).webp',
            'img/sleeves/_Sleeve (7).webp',
            'img/sleeves/_Sleeve (8).webp',
            'img/sleeves/_Sleeve (9).webp',
            'img/sleeves/_Sleeve (10).webp',
            'img/sleeves/_Sleeve (11).webp',
            'img/sleeves/_Sleeve (12).webp',
            'img/sleeves/_Sleeve (13).webp',
            'img/sleeves/_Sleeve (14).webp',
            'img/sleeves/_Sleeve (15).webp',
            'img/sleeves/_Sleeve (16).webp',
            'img/sleeves/_Sleeve (17).webp',
            'img/sleeves/_Sleeve (18).webp',
            'img/sleeves/_Sleeve (19).webp',
            'img/sleeves/_Sleeve (20).webp',
            'img/sleeves/_Sleeve (21).webp',
            'img/sleeves/_Sleeve (22).webp',
            'img/sleeves/_Sleeve (23).webp',
            'img/sleeves/_Sleeve (24).webp',
            'img/sleeves/_Sleeve (24).webp',
            'img/sleeves/_Sleeve (25).webp',
            'img/sleeves/_Sleeve (26).webp',
            'img/sleeves/_Sleeve (27).webp',
            'img/sleeves/_Sleeve (28).webp',
            'img/sleeves/_Sleeve (29).webp',
            'img/sleeves/_Sleeve (30).webp',
            'img/sleeves/_Sleeve (31).webp',
            'img/sleeves/_Sleeve (32).webp',
            'img/sleeves/_Sleeve (33).webp',
            'img/sleeves/_Sleeve (34).webp',
            'img/sleeves/_Sleeve (35).webp',
            'img/sleeves/_Sleeve (36).webp',
            'img/sleeves/_Sleeve (37).webp',
            'img/sleeves/_Sleeve (38).webp',
            'img/sleeves/_Sleeve (39).webp',
            'img/sleeves/_Sleeve (40).webp',
            'img/sleeves/_Sleeve (41).webp',
            'img/sleeves/_Sleeve (42).webp',
            'img/sleeves/_Sleeve (43).webp',
            'img/sleeves/_Sleeve (44).webp',
            'img/sleeves/_Sleeve (45).webp',
            'img/sleeves/_Sleeve (46).webp',
            'img/sleeves/_Sleeve (47).webp',
            'img/sleeves/_Sleeve (48).webp',
            'img/sleeves/_Sleeve (49).webp',
            'img/sleeves/_Sleeve (50).webp',
            'img/sleeves/_Sleeve (51).webp',
            'img/sleeves/_Sleeve (52).webp',
            'img/sleeves/_Sleeve (53).webp',
            'img/sleeves/_Sleeve (54).webp',
            'img/sleeves/_Sleeve (55).webp',
            'img/sleeves/_Sleeve (56).webp',
            'img/sleeves/_Sleeve (57).webp',
            'img/sleeves/_Sleeve (58).webp',
            'img/sleeves/_Sleeve (59).webp',
            'img/sleeves/_Sleeve (60).webp',
            'img/sleeves/_Sleeve (61).webp',
            'img/sleeves/_Sleeve (62).webp',
        ]

        for sleeve_path in default_sleeves:
            if not Sleeve.query.filter_by(sleeve=sleeve_path).first():
                db.session.add(Sleeve(sleeve=sleeve_path, sleeve_type='Buddyfight'))

        db.session.commit()
        print("Default sleeves added to the database.")
    

    try:
        with app.app_context(): 
            seed_sleeves()
        return jsonify({"message": "Sleeves added successfully!"}), 200
    except Exception as e:
        app.logger.error(f"Error seeding sleeves: {e}")
        return jsonify({"error": "Failed to add sleeves", "message": str(e)}), 500

@app.route('/admin/sleeves/delete/<int:sleeve_id>', methods=['POST'])
@login_required
@admin_required
def delete_sleeve(sleeve_id):
    sleeve = Sleeve.query.get(sleeve_id)
    if not sleeve:
        return jsonify({"error": "Sleeve not found"}), 404

    sleeve_path = os.path.join(app.config['UPLOAD_SLEEVE'], os.path.basename(sleeve.sleeve))

    if os.path.exists(sleeve_path):
        os.remove(sleeve_path)

    db.session.delete(sleeve)
    db.session.commit()

    return jsonify({"message": "Sleeve deleted successfully!"})

@app.route('/update_session', methods=['POST'])
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
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

@app.route('/uploads/profile_images/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/error')
def error():
    return render_template('error.html')

@app.route('/trigger-error/<int:error>')
def trigger_404(error):
    abort(error)  

if __name__ == '__main__':
    with app.app_context():
        db.create_all(bind_key='cards')
        db.create_all(bind_key='item')
        db.create_all(bind_key='users')
        db.create_all(bind_key='reports')
    socketio.run(app, host="0.0.0.0", port=8000, debug=True)
