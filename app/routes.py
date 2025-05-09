from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, Team, Competition
from . import db, bcrypt
from itertools import combinations
import random
from datetime import datetime
from . import route_ManageUser

main = Blueprint('main', __name__)

# 首頁轉導至登入
@main.route('/')
def home():
    return redirect(url_for('main.login'))

# 登入
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('登入失敗，請檢查帳號密碼')
    return render_template('login.html')

# 註冊（預設為隊長）
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            flash('帳號已存在，請使用其他名稱')
            return redirect(url_for('main.register'))
            
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=request.form['username'], password=hashed_pw, name = request.form.get('name'), role='visitor')
        db.session.add(user)
        db.session.commit()
        flash('註冊成功，請登入')
        return redirect(url_for('main.login'))
    return render_template('register.html')

# 顯示抽籤頁面
@main.route('/admin/draw_teams', methods=['GET'])
@login_required
def show_draw_teams_page():
    if current_user.role != 'admin':
        return "❌ 無權限操作", 403
    return render_template('draw_teams.html')


# 處理抽籤 POST 請求
@main.route('/admin/draw_teams', methods=['GET', 'POST'])
@login_required
def draw_teams():
    if current_user.role != 'admin':
        return "❌ 無權限操作", 403

    if request.method == 'POST':
        team_type = request.form.get('team_type')
        if not team_type:
            flash("❌ 請選擇分組類別")
            return redirect(url_for('main.draw_teams'))

        # 取得所有該類別隊伍，按名稱排序
        teams = Team.query.filter_by(team_type=team_type).order_by(Team.name).all()
        random.shuffle(teams)

        # 分 A / B 組
        for i, team in enumerate(teams):
            team.team_cycle = 'A' if i % 2 == 0 else 'B'
        db.session.commit()

        # 重新查詢分完組的隊伍
        group_a = Team.query.filter_by(team_type=team_type, team_cycle='A').order_by(Team.name).all()
        group_b = Team.query.filter_by(team_type=team_type, team_cycle='B').order_by(Team.name).all()

        return render_template('draw_teams.html', team_type=team_type, group_a=group_a, group_b=group_b)

    return render_template('draw_teams.html')

# 還在處理當中
@main.route('/admin/create_competition', methods=['GET', 'POST'])
@login_required
def create_competition():
    if current_user.role != 'admin':
        return "❌ 無權限進入", 403

    teams = Team.query.all()

    if request.method == 'POST':
        team1_id = int(request.form['team1'])
        team2_id = request.form.get('team2')
        if not team2_id:
            flash("❌ 請選擇隊伍 2")
            return redirect(url_for('main.create_match'))
        team2_id = int(team2_id)
        referee_id = int(request.form['referee'])
        match_time_str = request.form.get("match_time")
        match_time = datetime.strptime(match_time_str, "%Y-%m-%dT%H:%M")

        team1 = Team.query.get(team1_id)
        team2 = Team.query.get(team2_id)
        referee = Team.query.get(referee_id)

        # 限制條件檢查
        if team1.id == team2.id:
            flash("❌ 隊伍不可相同")
            return redirect(url_for('main.create_competition'))

        if team1.team_type != team2.team_type:
            flash("❌ 必須同為男排或同為女排")
            return redirect(url_for('main.create_competition'))

        if team1.team_cycle != team2.team_cycle:
            flash("❌ 必須同為 A 組或同為 B 組")
            return redirect(url_for('main.create_competition'))

        if referee.id in [team1.id, team2.id]:
            flash("❌ 裁判不能是參賽隊伍")
            return redirect(url_for('main.create_competition'))

        if referee.team_type != team1.team_type:
            flash("❌ 裁判需與比賽隊伍為相同排別（男排或女排）")
            return redirect(url_for('main.create_competition'))

        if referee.team_cycle == team1.team_cycle:
            flash("❌ 裁判必須與參賽隊伍不同組別")
            return redirect(url_for('main.create_competition'))

        # 建立比賽
        match = Competition(
            team1_id=team1.id,
            team2_id=team2.id,
            referee_id=referee.id,
            match_time=match_time
        )
        db.session.add(match)
        db.session.commit()
        flash("比賽已建立成功")
        return redirect(url_for('main.create_competition'))

    return render_template('create_competition.html', teams=teams)

# Dashboard 主頁（根據角色顯示）
@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)

# 登出
@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))