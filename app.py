# Importing necessary libraries
from flask import Flask
from flask_socketio import SocketIO
import os, sys
# Personal Libraries
from models import db
from error import handle_error
from cardExtractor import *
from globals import chat_rooms, game_rooms, user_rooms
from routes import routes
from sockets import ChatRooms, ArenaGameplay, Main, LobbyCreation

# Initialize Flask app and database
app = Flask(__name__, template_folder='templates', static_folder="static", static_url_path='/')
app.register_blueprint(routes, url_prefix='/')

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

sys.setrecursionlimit(1500)
db.init_app(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Profile Picture
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'profile_images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Sleeves
UPLOAD_SLEEVE = os.path.join('static', 'img', 'sleeves')
app.config['UPLOAD_SLEEVE'] = UPLOAD_SLEEVE

# For chat Rooms and Arena
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*", logger=True, engineio_logger=True)
os.environ['GEVENT_SUPPORT'] = 'True'
default = Main(socketio)
chatoomSocket = ChatRooms(socketio, chat_rooms)
socketio.on_namespace(chatoomSocket)

lobbySocket = LobbyCreation(socketio, game_rooms, user_rooms)

arenagameplaySocket = ArenaGameplay(socketio, game_rooms, user_rooms)

# Error handling
app.register_error_handler(Exception, handle_error)

if __name__ == '__main__':
    with app.app_context():
        db.create_all(bind_key='cards')
        db.create_all(bind_key='item')
        db.create_all(bind_key='users')
        db.create_all(bind_key='reports')
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)