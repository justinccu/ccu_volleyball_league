from . import db
from flask_login import UserMixin
from . import login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    
    # 帳號：唯一、登入用
    username = db.Column(db.String(20), unique=True, nullable=False)
    
    # 密碼：加密存入
    password = db.Column(db.String(60), nullable=False)
    
    # 使用者顯示姓名（可重複）
    name = db.Column(db.String(50), nullable=False)
    
    # 角色：admin / captain / member / visitor
    role = db.Column(db.String(10), nullable=False)
    
    # 所屬隊伍（可為 None）
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)

class Team(db.Model):
    __tablename__ = 'team'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    captain_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    captain = db.relationship('User', foreign_keys=[captain_id], backref='captain_of_team')
    members = db.relationship('User', backref='team', lazy=True, foreign_keys='User.team_id')