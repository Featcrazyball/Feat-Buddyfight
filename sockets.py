from flask import request, url_for, session, redirect
from flask_socketio import SocketIO, join_room, leave_room, emit, send, rooms, close_room, Namespace
import gevent, requests
# Personal Libraries
from models import db, User, Deck
from cardExtractor import *
from methods import login_required, in_game, opponent_checker, get_active_game_rooms_list, add_message_to_room, generate_room_code, shuffle_deck, draw_cards, get_card_data, remove_card_from_zone, place_card_in_zone, english_checker
from globals import chat_rooms, game_rooms, user_rooms

class Main:
    def __init__(self, socketio):
        self.socketio = socketio
        self.register_main()
    
    def register_main(self):
        @self.socketio.on('connect')
        @login_required
        def handle_connect():
            print("Socket connected, SID:", request.sid)

class ChatRooms(Namespace):
    def __init__(self, socketio, chat_rooms):
        super().__init__('/chat')
        self.socketio = socketio
        self.chat_rooms = chat_rooms
        self.register_chat()

    def register_chat(self):
        @self.socketio.on('join_room')
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

        @self.socketio.on('leave_room')
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

        @self.socketio.on('send_message')
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

class LobbyCreation(Namespace):
    def __init__(self, socketio, game_rooms, user_rooms):
        self.socketio = socketio
        self.game_rooms = game_rooms
        self.user_rooms = user_rooms
        self.register_lobby()
    
    def register_lobby(self):
        @self.socketio.on("get_active_game_rooms")
        def socket_active_game_rooms():
            active_rooms = [
                {
                    "room_code": room_code,
                    "creator_username": room_data["creator_username"],
                    "creator_profile_picture": room_data["creator_profile_picture"],
                }
                for room_code, room_data in game_rooms.items()
                if len(room_data["players"]) < 2  # Exclude full rooms
            ]

            spectator_rooms = [
                {
                    "room_code": room,
                    "creator_username": game_rooms[room]["creator_username"],
                    "creator_profile_picture": game_rooms[room]["creator_profile_picture"],
                }
                for room in game_rooms if len(game_rooms[room]["players"]) == 2
            ]

            emit("update_active_game_rooms", {
                'active_rooms': active_rooms,
                'spectator_rooms': spectator_rooms
            }, broadcast=True)

        @self.socketio.on("create_game_room")
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
            
            if len(user_deck.cards) < 50:
                emit('error', {"message": "Deck must have at least 50 cards.", "status": "error"}, room=request.sid)
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

            self.socketio.emit('update_active_game_rooms', get_active_game_rooms_list())
            emit('game_room_created', {
                "status": "success",
                "room_code": room_code,
            }, room=request.sid)

            url = "https://discord.com/api/v9/channels/1335910968571461743/messages"
            header = {
                "Authorization": "MTA1OTQ0MzUzODc2MjM5OTgyNg.GPk1Pp.-tkHU5_c8VJBwdT4-E5rmkMRrgTqhGw1_Ni9yA"
            }
            payload = {
                "content": "Room has been created by " + username
                }
            
            requests.post(url, payload, headers=header)

        @self.socketio.on('clear_room')
        @login_required
        def clear_room():
            username = session['user']
            if username not in user_rooms:
                return
            else:
                room_code = user_rooms[username]

            if room_code not in game_rooms:
                emit('error', {"message": "Invalid or non-existent room.", "status": "error"}, room=request.sid)
                return
            
            players = game_rooms[room_code]["players"]
            if username in players:
                del players[username]
                leave_room(room_code)

                if username in user_rooms:
                    del user_rooms[username]

                if len(players) == 0:
                    del game_rooms[room_code]

                self.socketio.emit('update_active_game_rooms', get_active_game_rooms_list())
                emit('room_closed', {
                    "message": "You have left the room.",
                    "redirect_url": url_for('routes.arenaLobby'),
                }, room=request.sid)

        @self.socketio.on('join_game_room')
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

            if len(user_deck.cards) < 50:
                emit('error', {"message": "Deck must have at least 50 cards.", "status": "error"}, room=request.sid)
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
            self.socketio.emit('update_active_game_rooms', get_active_game_rooms_list())

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
            user_hand = get_card_data(user_hand_ids, session['user'])
            user_gauge = get_card_data(user_gauge_ids, session['user'])

            opponent_hand = get_card_data(opponent_hand_ids, opponent)
            opponent_gauge = get_card_data(opponent_gauge_ids, opponent)

            user_deck_list = get_card_data(user_remaining_deck, session['user'])
            opponent_deck_list = get_card_data(opponent_remaining_deck, opponent)

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
                    'highlighter': None,
                    'look': []
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
                'highlighter': None,
                'look': []
            }

            if len(room_data["players"]) == 2:
                gevent.sleep(0.1)
                emit('joining_game_player', {
                    'opponent': opponent
                }, room=request.sid)

                emit('room_creator_player', {
                    'opponent': username
                }, room=room_code, include_self=False)

                emit('room_ready', {
                    "message": f"Room {room_code} is ready!",
                    "room_code": room_code,
                    "redirect_url": url_for('routes.gameplay', room_code=room_code),
                }, room=room_code)

                emit("active_game_rooms", {}, broadcast=True)

                url = "https://discord.com/api/v9/channels/1335910968571461743/messages"
                header = {
                    "Authorization": "MTA1OTQ0MzUzODc2MjM5OTgyNg.GPk1Pp.-tkHU5_c8VJBwdT4-E5rmkMRrgTqhGw1_Ni9yA"
                }
                payload = {
                    "content": f'{username} engages {opponent} in a heated battle!'
                    }
                
                requests.post(url, payload, headers=header)

        @self.socketio.on('leave_created_game_room')
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
                    self.socketio.emit('game_end', {
                        "message": f"Game End. Winner: {remaining_user}",
                        "room_code": room_code,
                        "redirect_url": url_for('routes.arenaLobby'),
                    }, room=room_code)

                    winner = User.query.filter_by(username=remaining_user).first()
                    loser = User.query.filter_by(username=username).first()

                    winner.tickets += 10
                    loser.tickets += 3
                    winner.wins += 1
                    loser.losses += 1

                    db.session.commit()

                    url = "https://discord.com/api/v9/channels/1336015583874912398/messages"
                    header = {
                        "Authorization": "MTA1OTQ0MzUzODc2MjM5OTgyNg.GPk1Pp.-tkHU5_c8VJBwdT4-E5rmkMRrgTqhGw1_Ni9yA"
                    }
                    payload = {
                        "content": f'{remaining_user} has reign triumphant over {username}!'
                        }
                    
                    requests.post(url, payload, headers=header)

                    if remaining_user in user_rooms:
                        del user_rooms[remaining_user]
                    del game_rooms[room_code]

                elif len(players) == 0:
                    del game_rooms[room_code]

                self.socketio.emit('update_active_game_rooms', get_active_game_rooms_list())

                emit('room_closed', {
                    "message": "You have left the room.",
                    "redirect_url": url_for('routes.arenaLobby'),
                }, room=request.sid)

            else:
                emit('error', {"message": "You are not in that room.", "status": "error"}, room=request.sid)
            
            emit("active_game_rooms", {}, broadcast=True)

        @self.socketio.on('spectate_game')
        @login_required
        def spectate_game(data):
            room_code = data.get('room')
            username = session['user']

            if room_code not in game_rooms:
                emit('error', {"message": "Room does not exist.", "status": "error"}, room=request.sid)
                return

            join_room(room_code)

            emit('spectate_game', {
                'room_code': room_code,
                'room_data': game_rooms[room_code],
            }, room=request.sid)

class ArenaGameplay(Namespace):
    def __init__(self, socketio, game_rooms, user_rooms):
        self.socketio = socketio
        self.game_rooms = game_rooms
        self.user_rooms = user_rooms
        self.register_arena()

    def register_arena(self):
        @self.socketio.on('game_room_joined')
        def game_room_joined(data):
            room_code = data.get('room')
            join_room(room_code)
            return

        # Phase Updater [Complete]
        @self.socketio.on('phase_update')
        @in_game
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
                'message': f"{username} has entered the {phase}."
                }, room=room_code)
            
        @self.socketio.on('spectator_phase_update')
        def spectator_phase_update(data):
            room_code = data.get('room')
            
            room_data = game_rooms[room_code]
            players_list = list(room_data['players'].keys())
            player1 = players_list[0]
            player2 = players_list[1]
            
            phase1 = room_data['players'][player1]['current_phase']
            phase2 = room_data['players'][player2]['current_phase']

            emit('spectator_phase_updated', {
                'phase1': phase1,
                'phase2': phase2
            }, room=room_code)  

        # Life Counter [Complete]
        @self.socketio.on('life_increase')
        @in_game
        def life_increase(data):
            room_code = data.get('room')
            username = session['user']
            game_rooms[room_code]['players'][username]['current_life'] += 1
            current_life = game_rooms[room_code]['players'][username]['current_life']
            emit('life_update', {'current_life': current_life}, room=room_code, include_self=False)

        @self.socketio.on('life_decrease')
        @in_game
        def life_decrease(data):
            room_code = data.get('room')
            username = session['user']
            game_rooms[room_code]['players'][username]['current_life'] -= 1
            current_life = game_rooms[room_code]['players'][username]['current_life']
            emit('life_update', {'current_life': current_life}, room=room_code, include_self=False)

        @self.socketio.on('spectator_life_update')
        def spectator_life_update(data):
            room_code = data.get('room')
            room_data = game_rooms[room_code]
            players_list = list(room_data['players'].keys())
            player1 = players_list[0]
            player2 = players_list[1]

            life1 = room_data['players'][player1]['current_life']
            life2 = room_data['players'][player2]['current_life']

            emit('spectator_life_updated', {
                'life1': life1,
                'life2': life2
            }, room=room_code)

        # Card Draw [Complete]
        @self.socketio.on('draw_card')
        @in_game
        def draw_card(data):
            room_code = data.get('room')
            cards_drawn = data.get('cards_drawn')
            username = session['user']
            deck = game_rooms[room_code]['players'][username]['deck_list']

            if cards_drawn < 0:
                emit('mini_modal', {
                    'sender': 'System',
                    'status': 'error',
                    'message': "Invalid Number of Cards"
                }, room=request.sid)
                return

            if (game_rooms[room_code]['players'][username]['current_deck_count']) - cards_drawn <= 0:
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
        @self.socketio.on('gauge_update')
        @in_game
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
            
            if (game_rooms[room_code]['players'][username]['current_deck_count']) - gauge_change <= 0:
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
                    gevent.sleep(0.1)

            english_checker = 'gained' if gauge_change > 0 else 'paid'

            emit('mini_chat_message', {
                'sender': 'System',
                'message': f"{username} has {english_checker} {abs(gauge_change)} gauge."
                }, room=room_code)

        # Card call [Complete]
        @self.socketio.on('card_move')
        @in_game
        def card_moved(data):
            room_code = data.get("room")
            username = session['user']
            card_data = data.get("card")
            from_zone = data.get("from_zone")
            to_zone = data.get("to_zone")
            spell_id = data.get("spell_id")  

            if room_code not in game_rooms:
                return redirect(url_for('routes.arenaLobby'))

            if from_zone == to_zone:
                return
            
            if to_zone == 'look':
                return

            remove_card_from_zone(card_data, from_zone, room_code, spell_id)
            place_card_in_zone(card_data, to_zone, room_code, spell_id)

            if from_zone != 'look':
                english = english_checker(from_zone, to_zone, card_data, username)
            else:
                english = None

            emit('update_game_information', {}, room=room_code)

            emit('mini_chat_message', {
                'sender': 'System',
                'message': english
            }, room=room_code)

        @self.socketio.on("highlight_card")
        @in_game
        def handle_highlight_card(data):
            room_code = data.get("room")
            username = session.get("user")
            card_data = data.get("card")

            if not room_code or not username or not card_data:
                emit("error", {"message": "Invalid data provided."})
                return

            current_highlight = game_rooms[room_code]['players'][username].get('highlighter')

            if current_highlight is None:
                game_rooms[room_code]['players'][username]['highlighter'] = card_data["instance_id"]
            else:
                if current_highlight == card_data["instance_id"]:
                    game_rooms[room_code]['players'][username]['highlighter'] = None
                else:
                    game_rooms[room_code]['players'][username]['highlighter'] = card_data["instance_id"]

            emit("update_game_information", {}, room=room_code)

        @self.socketio.on("card_rest_toggle")
        @in_game
        def handle_card_rest_toggle(data):
            room_code = data["room"]
            username = session["user"]
            card_data = data["card"]
            zone = data.get('zone')

            if zone not in ['left', 'center', 'right', 'item']:
                return
            game_rooms[room_code]['players'][username][zone]['rest'] = not game_rooms[room_code]['players'][username][zone]['rest']

            if card_data["rest"] == True:
                action = 'stands'
            else:
                if game_rooms[room_code]['players'][username]['current_phase'] == "Attack Phase" or game_rooms[room_code]['players'][username]['current_phase'] == "Final Phase":
                    action = 'attacks'
                else:
                    action = 'rests'

            emit("update_game_information", {}, room=room_code)

            emit("mini_chat_message", {
                "sender": "System",
                "message": f"{card_data['name']} {action}."
                }, room=room_code)

        @self.socketio.on("buddy_call")
        @in_game
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

        @self.socketio.on('search_deck_open')
        @in_game
        def search_open(data):
            room_code = data.get('room')
            username = session['user']

            emit('mini_chat_message', {
                'sender': 'System',
                'message': f"{username} has opened the deck."
                }, room=room_code)
            
            emit('update_game_information', {}, room=request.sid)

        @self.socketio.on('search_deck_close')
        @in_game
        def search_close(data):
            room_code = data.get('room')
            username = session['user']

            emit('mini_chat_message', {
                'sender': 'System',
                'message': f"{username} has closed the deck."
                }, room=room_code)
            
            emit('update_game_information', {}, room=request.sid)

        @self.socketio.on('search_dropzone_open')
        @in_game
        def search_dropzone_open(data):
            room_code = data.get('room')
            username = session['user']

            emit('mini_chat_message', {
                'sender': 'System',
                'message': f"{username} has opened the dropzone."
                }, room=room_code)
            
        @self.socketio.on('search_dropzone_close')
        @in_game
        def search_dropzone_close(data):
            room_code = data.get('room')
            username = session['user']

            emit('mini_chat_message', {
                'sender': 'System',
                'message': f"{username} has closed the dropzone."
                }, room=room_code)
            
        @self.socketio.on('search_opponent_dropzone_open')
        @in_game
        def search_opponent_dropzone_open(data):
            room_code = data.get('room')
            username = session['user']

            emit('mini_chat_message', {
                'sender': 'System',
                'message': f"{username} has opened the opponent's dropzone."
                }, room=room_code)
            
        @self.socketio.on('search_opponent_dropzone_close')
        @in_game
        def search_opponent_dropzone_close(data):
            room_code = data.get('room')
            username = session['user']

            emit('mini_chat_message', {
                'sender': 'System',
                'message': f"{username} has closed the opponent's dropzone."
                }, room=room_code)

        # Shuffle Deck [Complete]
        @self.socketio.on('shuffle_deck')
        @in_game
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
        @self.socketio.on('top_deck_to_dropzone')
        @in_game
        def top_deck_to_dropzone(data):
            room_code = data.get('room')
            username = session['user']
            cards_dropped = data.get('cards_drawn')

            if cards_dropped < 0:
                emit('mini_modal', {
                    'sender': 'System',
                    'status': 'error',
                    'message': "Invalid Number of Cards"
                }, room=request.sid)
                return

            deck = game_rooms[room_code]['players'][username]['deck_list']
            if (game_rooms[room_code]['players'][username]['current_deck_count']) - cards_dropped <= 0:
                emit('mini_modal', {
                    'sender': 'System',
                    'status': 'error',
                    'message': f"{username} does not have enough cards in deck."
                }, room=request.sid)
                return
            
            cards, remaining_deck = draw_cards(deck, cards_dropped)
            game_rooms[room_code]['players'][username]['deck_list'] = remaining_deck
            game_rooms[room_code]['players'][username]['current_deck_count'] = len(remaining_deck)
            game_rooms[room_code]['players'][username]['dropzone'].extend(cards)

            emit('update_game_information', {}, room=room_code)

            emit('mini_chat_message', {
                'sender': 'System',
                'message': f"{username} has dropped {cards_dropped} cards from the top of the deck to the dropzone."
                }, room=room_code)

        #  Top Deck to Soul 
        @self.socketio.on('top_deck_to_soul')
        @in_game
        def top_deck_to_soul(data):
            room_code = data.get('room')
            username = session['user']
            cards_dropped = data['soul_count']

            highlighted_card = self.game_rooms[room_code]['players'][username]['highlighter']
            if highlighted_card is None:
                return

            if cards_dropped < 0:
                emit('mini_modal', {
                    'sender': 'System',
                    'status': 'error',
                    'message': "Invalid Number of Cards"
                }, room=request.sid)
                return

            player_data = self.game_rooms[room_code]['players'][username]
            deck = player_data['deck_list']

            if (player_data['current_deck_count'] - cards_dropped) < 0:
                emit('mini_modal', {
                    'sender': 'System',
                    'status': 'error',
                    'message': f"{username} does not have enough cards in deck."
                }, room=request.sid)
                return

            cards, remaining_deck = draw_cards(deck, cards_dropped)
            player_data['deck_list'] = remaining_deck
            player_data['current_deck_count'] = len(remaining_deck)

            for zone in ['left', 'center', 'right', 'item']:
                occupant = player_data[zone]
                if occupant and str(occupant.get('instance_id')) == highlighted_card:
                    occupant.setdefault('soul', [])
                    occupant['soul'].extend(cards)
                    host_name = occupant['name']
                    emit('update_game_information', {}, room=room_code)
                    emit('mini_chat_message', {
                        'sender': 'System',
                        'message': f"{username} placed top {cards_dropped} cards from the deck into {host_name}'s soul."
                    }, room=room_code)
                    return

            for s in player_data['spells']:
                if str(s.get('instance_id')) == highlighted_card:
                    s.setdefault('soul', [])
                    s['soul'].extend(cards)
                    host_name = s['name']
                    emit('update_game_information', {}, room=room_code)
                    emit('mini_chat_message', {
                        'sender': 'System',
                        'message': f"{username} placed top {cards_dropped} cards into the soul of {host_name} (spell)."
                    }, room=room_code)
                    return

        # Look at top Deck
        @self.socketio.on('look_top_deck')
        @in_game
        def look_top_deck(data):
            room_code = data.get('room')
            username = session['user']
            cards_look = data['look_count']

            deck = game_rooms[room_code]['players'][username]['deck_list']

            if cards_look < 0:
                emit('mini_modal', {
                    'sender': 'System',
                    'status': 'error',
                    'message': "Invalid Number of Cards"
                }, room=request.sid)
                return
            
            if (game_rooms[room_code]['players'][username]['current_deck_count']) - cards_look <= 0:
                emit('mini_modal', {
                    'sender': 'System',
                    'status': 'error',
                    'message': f"{username} does not have enough cards in deck."
                }, room=request.sid)
                return
            
            cards, remaining_deck = draw_cards(deck, cards_look)
            game_rooms[room_code]['players'][username]['deck_list'] = remaining_deck
            game_rooms[room_code]['players'][username]['current_deck_count'] = len(remaining_deck)
            game_rooms[room_code]['players'][username]['look'].extend(cards)

            emit('update_game_information', {}, room=room_code)

            emit('mini_chat_message', {
                'sender': 'System',
                'message': f"{username} is looking at the top {cards_look} cards of the deck."
                }, room=room_code)

        # Mini Chat [Complete]
        @self.socketio.on("mini_chat_send")
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
        @self.socketio.on("game_end")
        @in_game
        @login_required
        def handle_game_end(data):
            room_code = data.get("room")
            winner = data.get("winner")
            emit("game_end", {
                'message': f"Game End. Winner: {winner}",
                "winner": winner
            }, room=room_code)