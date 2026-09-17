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

# Determine the database folder directory path based on environment
if os.environ.get('FLY_APP_NAME'):
    # Production path utilizing the persistent Fly Volume
    DB_DIR = '/data'
else:
    # Local fallback path inside your project's instance directory
    DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'instance'))

# Ensure the database storage folder exists before initializing SQLite engines
os.makedirs(DB_DIR, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(DB_DIR, "default.db")}'  
app.config['SQLALCHEMY_BINDS'] = {
    'users': f'sqlite:///{os.path.join(DB_DIR, "users.db")}',
    'cards': f'sqlite:///{os.path.join(DB_DIR, "buddyfight_cards.db")}',
    'reports': f'sqlite:///{os.path.join(DB_DIR, "reports.db")}',
    'item': f'sqlite:///{os.path.join(DB_DIR, "items.db")}',
    'episodes': f'sqlite:///{os.path.join(DB_DIR, "episodes.db")}',
    'matches': f'sqlite:///{os.path.join(DB_DIR, "matches.db")}'
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
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*", logger=True, engineio_logger=True, message_queue=os.getenv("REDIS_URL"))
os.environ['GEVENT_SUPPORT'] = 'True'
default = Main(socketio)
chatoomSocket = ChatRooms(socketio, chat_rooms)
socketio.on_namespace(chatoomSocket)

lobbySocket = LobbyCreation(socketio, game_rooms, user_rooms)

arenagameplaySocket = ArenaGameplay(socketio, game_rooms, user_rooms)

# Error handling
app.register_error_handler(Exception, handle_error)

with app.app_context():
    db.create_all(bind_key='cards')
    db.create_all(bind_key='item')
    db.create_all(bind_key='users')
    db.create_all(bind_key='reports')
    db.create_all(bind_key='episodes')
    db.create_all(bind_key='matches')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
