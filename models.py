from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from pytz import timezone

db = SQLAlchemy()

class Card(db.Model):
    __bind_key__ = 'cards'
    id = db.Column(db.Integer, primary_key=True)
    card_no = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    rarity = db.Column(db.String(50))
    world = db.Column(db.String(100))
    attribute = db.Column(db.String(100))
    size = db.Column(db.Integer)
    defense = db.Column(db.Integer)
    critical = db.Column(db.Integer)
    power = db.Column(db.Integer)
    ability_effect = db.Column(db.Text)
    flavor_text = db.Column(db.Text)
    illustrator = db.Column(db.String(200))
    image_url = db.Column(db.String(500))
    detail_url = db.Column(db.String(500))
    type = db.Column(db.String)
    is_horizontal = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "card_no": self.card_no,
            "name": self.name,
            "rarity": self.rarity,
            "world": self.world,
            "attribute": self.attribute,
            "size": self.size,
            "defense": self.defense,
            "critical": self.critical,
            "power": self.power,
            "ability_effect": self.ability_effect,
            "flavor_text": self.flavor_text,
            "illustrator": self.illustrator,
            "image_url": self.image_url,
            "detail_url": self.detail_url,
            "type": self.type,
            "is_horizontal": self.is_horizontal
        }
    
class Item(db.Model):
    __bind_key__ = 'item'  
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    count = db.Column(db.Integer, nullable=False)  
    price = db.Column(db.Float(precision=2), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": round(self.price, 2)
        }

class Deck(db.Model):
    __tablename__ = 'decks'
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), db.ForeignKey('user.username', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    cards = db.Column(db.JSON, default=[]) 
    flag = db.Column(db.String(100), nullable=False)
    selected = db.Column(db.Boolean, nullable=True)
    flagLink = db.Column(db.String, nullable=True, default='img/Cardback.webp')
    buddy_card_id = db.Column(db.Integer, nullable=True)  
    initial_life = db.Column(db.Integer, nullable=False, default=10)
    initial_hand_size = db.Column(db.Integer, nullable=False, default=6)
    initial_gauge = db.Column(db.Integer, nullable=False, default=2)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "cards": self.cards,
            "flag": self.flag,
            "selected":self.selected,
            "flagLink":self.flagLink
        }

class Sleeve(db.Model):
    __tablename__ = 'sleeves'
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    sleeve = db.Column(db.String(500), nullable=True, default='img/sleeves/9Cardback.webp')
    sleeve_type = db.Column(db.String(500), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "sleeve": self.sleeve,
            "sleeve_type":self.sleeve_type
        }

class PaymentHistory(db.Model):
    __bind_key__ = 'users'
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), db.ForeignKey('user.username'), nullable=False) 
    item_id = db.Column(db.Integer, nullable=False) 
    item_price = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone("Asia/Singapore")))

    user = db.relationship('User', backref='payment_history', lazy=True) 

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "item_id": self.item_id,
            "item_price": self.item_price,
            "timestamp": self.timestamp.isoformat(),
            "item_name": self.item.name if self.item else None
        }
    
class Match(db.Model):
    __bind_key__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    winner = db.Column(db.String(150), nullable=True)
    loser = db.Column(db.String(150), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone("Asia/Singapore")))

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "winner": self.winner,
            "loser": self.loser,
            "timestamp": self.timestamp.isoformat()
        }

class User(db.Model):
    __bind_key__ = 'users'
    username = db.Column(db.String(150), primary_key=True, nullable=False) 
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='user')  
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    tickets = db.Column(db.Integer, default=100)
    profile_image = db.Column(db.String(500), nullable=True, default='uploads/default_profile.jpg')
    unlocked_cards = db.Column(db.JSON, default=[])
    selected_deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=True)
    selected_sleeve_id = db.Column(db.Integer, db.ForeignKey('sleeves.id'), nullable=True, default=1)

    decks = db.relationship('Deck', backref='user', foreign_keys=[Deck.username], lazy=True)
    selected_deck = db.relationship('Deck', foreign_keys=[selected_deck_id], backref='selected_by', lazy=True)
    selected_sleeve = db.relationship('Sleeve', foreign_keys=[selected_sleeve_id], backref='selected_by', lazy=True)

    def to_dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "wins": self.wins,
            "losses": self.losses,
            "tickets": self.tickets,
            "profile_image": self.profile_image
        }
    
# Report Model
class Report(db.Model):
    __bind_key__ = 'reports'
    id = db.Column(db.Integer, primary_key=True) 
    user_reporting = db.Column(db.String(20), nullable=True)
    user_being_reported = db.Column(db.String(20), nullable=True)
    report_type = db.Column(db.String(50), nullable=False)  
    detail = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_reporting": self.user_reporting,
            "user_being_reported": self.user_being_reported,
            "report_type": self.report_type,
            "detail": self.detail,
        }
    
class Episode(db.Model):
    __bind_key__ = 'episodes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    video_url = db.Column(db.String(300), nullable=False)
    season = db.Column(db.Integer, nullable=True)