from . import db
from flask_login import UserMixin
from . import login_manager
from sqlalchemy import UniqueConstraint
from datetime import datetime
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    # 帳號
    username = db.Column(db.String(20), unique=True, nullable=False)
    # 密碼
    password = db.Column(db.String(60), nullable=False)
    # 姓名
    name = db.Column(db.String(50), nullable=False)
    # 角色
    role = db.Column(db.String(10), nullable=False)
    # 隊伍
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    # 系所
    department = db.Column(db.String(100), nullable=True)
    # 年級
    grade = db.Column(db.Integer, nullable=True)     
    # 男女排  
    gender = db.Column(db.String(10), nullable=True)

class Team(db.Model):
    __tablename__ = 'team'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    captain_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    team_type = db.Column(db.String(10), nullable=False)
    team_cycle = db.Column(db.String(10), nullable=True)
    __table_args__ = (
        UniqueConstraint('name', 'team_type', name='uq_team_name_type'),
    )
    captain = db.relationship('User', foreign_keys=[captain_id], backref='captain_of_team')
    members = db.relationship('User', backref='team', lazy=True, foreign_keys='User.team_id')


class Match(db.Model):
    __tablename__ = 'match'

    id = db.Column(db.Integer, primary_key=True)

    # 比賽雙方與裁判（皆為 Team）
    team1_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    referee_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)

    # 比賽類型（男排/女排）
    team_type = db.Column(db.String(10), nullable=False)

    # 時間與比賽結果
    match_time = db.Column(db.DateTime, nullable=True)
    total_sets = db.Column(db.Integer, nullable=True)

    # 分數欄位
    team1_set1 = db.Column(db.Integer, nullable=True)
    team2_set1 = db.Column(db.Integer, nullable=True)
    team1_set2 = db.Column(db.Integer, nullable=True)
    team2_set2 = db.Column(db.Integer, nullable=True)
    team1_set3 = db.Column(db.Integer, nullable=True)
    team2_set3 = db.Column(db.Integer, nullable=True)

    # 燈錢欄位
    team1_lamp_fee = db.Column(db.Integer, nullable=True)
    team2_lamp_fee = db.Column(db.Integer, nullable=True)

    # 勝負結果
    winner_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    loser_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)

    # 關聯設計
    team1 = db.relationship('Team', foreign_keys=[team1_id])
    team2 = db.relationship('Team', foreign_keys=[team2_id])
    referee = db.relationship('Team', foreign_keys=[referee_id])
    winner = db.relationship('Team', foreign_keys=[winner_id])
    loser = db.relationship('Team', foreign_keys=[loser_id])
    
    # Match 中新增以下欄位
    status = db.Column(db.String(20), default='pending')  # pending, waiting_confirm, confirmed
    team1_confirmed = db.Column(db.Boolean, default=False)
    team2_confirmed = db.Column(db.Boolean, default=False)
    result_submitted_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # 登錄人（裁判隊長）

    __table_args__ = (
        db.UniqueConstraint('team1_id', 'team2_id', name='unique_match_teams'),
    )
    
class JoinRequest(db.Model):
    __tablename__ = 'join_request'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending / approved / rejected

    user = db.relationship('User', backref='join_request')
    team = db.relationship('Team', backref='join_requests')
