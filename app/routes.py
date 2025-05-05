from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, Team, Competition
from . import db, bcrypt
from itertools import combinations
import random
from datetime import datetime

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

# 管理使用者（admin）=> 新增 + 顯示
@main.route('/admin/users', methods=['GET', 'POST'])
@login_required
def list_users():
    if current_user.role != 'admin':
        return "❌ 無權限查看使用者列表", 403

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        role = request.form['role']
        team_id = None
        team_type = request.form['team_type']
        department = request.form['department']
        grade = int(request.form['grade'])
        gender = request.form['gender']

        if User.query.filter_by(username=username).first():
            flash("⚠️ 此帳號已存在")
        else:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

            if role == 'captain':
                new_team_name = request.form.get('new_team_name')
                if not new_team_name:
                    flash("❌ 隊長必須輸入隊伍名稱")
                    return redirect(url_for('main.list_users'))

                existing_team = Team.query.filter_by(name=new_team_name, team_type=team_type).first()
                if existing_team:
                    flash("❌ 該隊伍名稱已被使用，請選擇其他名稱")
                    return redirect(url_for('main.list_users'))

                # 建立隊伍
                new_team = Team(name=new_team_name, team_type=team_type)
                db.session.add(new_team)
                db.session.commit()

                # 建立使用者，並指定 team_id
                user = User(username=username, name=name, password=hashed_pw, role=role, team_id=new_team.id, department=department, grade=grade, gender=gender)
                db.session.add(user)
                db.session.commit()

                # 補上隊長 ID
                new_team.captain_id = user.id
                db.session.commit()
                flash(f"已新增隊長 {username} 並建立隊伍 {new_team_name}")

            elif role == 'member':
                team_id = request.form.get('team_id')
                if not team_id:
                    flash("成員必須選擇隊伍")
                    return redirect(url_for('main.list_users'))

                user = User(username=username, name=name, password=hashed_pw, role=role, team_id=int(team_id), department=department, grade=grade, gender=gender)
                db.session.add(user)
                db.session.commit()
                flash(f"已新增成員 {username} 並加入隊伍")

            elif role == 'visitor':
                user = User(username=username, name=name, password=hashed_pw, role=role, department=department, grade=grade, gender=gender)
                db.session.add(user)
                db.session.commit()
                flash(f"已新增訪客 {username}")

            else:  # admin
                department = "管理單位"
                grade = 0
                gender = "不明"
                user = User(username=username, name=name, password=hashed_pw, role=role, department=department, grade=grade, gender=gender)
                db.session.add(user)
                db.session.commit()
                flash(f"已新增管理員 {username}")

    users = User.query.all()
    teams = Team.query.all()
    departments = [
    "中文系", "中文所", "外文系", "外文所", "歷史系", "歷史所", "哲學系", "哲學所", "語言所", "英語教學所",
    "台文創應所", "數學系", "應數所", "地震所", "物理系", "物理所", "統科所", "地環系", "地環所", "數學所",
    "分子生物所", "生醫系", "生醫所", "化暨生化系", "化暨生化所", "社福系", "社福所", "心理系", "心理所",
    "勞工系", "勞工所", "政治系", "政治所", "傳播系", "電傳所", "戰略所", "臨床心理所", "資工系", "資工所",
    "電機系", "電機所", "機械系", "機械所", "化工系", "化工所", "通訊系", "通訊所", "光機電所", "國際智慧製造碩士專班",
    "經濟學系", "國經所", "財金系", "財金所", "企管系", "企管所", "會資系", "會資所", "資管系", "資管所",
    "行銷與數位分析碩士班", "醫療資訊管理所", "法律系", "法律所", "財法系", "財法所", "成教系", "成教所",
    "教育所", "犯防系", "犯防所", "休閒教育所", "運競系", "課研所", "高齡教育所", "不分系"
    ]
    return render_template('list_users.html', users=users, teams=teams, departments=departments)


@main.route('/admin/assign_user', methods=['POST'])
@login_required
def assign_user():
    if current_user.role != 'admin':
        return "❌ 無權限操作", 403

    user_id = request.form.get('user_id')
    team_id = request.form.get('team_id')  # 空字串表示移除隊伍

    if not user_id:
        flash("❌ 請選擇使用者")
        return redirect(url_for('main.list_users'))

    user = User.query.get(int(user_id))
    if not user:
        flash("❌ 找不到指定使用者")
        return redirect(url_for('main.list_users'))

    if team_id == "":
        # 使用者移除隊伍
        user.team_id = None

        # 如果是 member，就轉為 visitor
        if user.role == 'member':
            user.role = 'visitor'

        flash(f"使用者 {user.username} 已從隊伍移除，角色已更新為 visitor")
    else:
        team = Team.query.get(int(team_id))
        if not team:
            flash("❌ 找不到指定隊伍")
            return redirect(url_for('main.list_users'))

        user.team_id = team.id

        # ✅ 若是 visitor 則改為 member（首次加入隊伍）
        if user.role == 'visitor':
            user.role = 'member'

        flash(f"✅ 使用者 {user.username} 已分配至隊伍 {team.name}")

    db.session.commit()
    return redirect(url_for('main.list_users'))

# 刪除使用者（admin）
@main.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return "❌ 無權限操作", 403

    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash("❌ 無法刪除管理員帳號")
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"🗑️ 使用者 {user.username} 已刪除")
    return redirect(url_for('main.list_users'))

@main.route('/admin/delete_team/<int:team_id>', methods=['POST'])
@login_required
def delete_team(team_id):
    if current_user.role != 'admin':
        return "❌ 無權限操作", 403

    team = Team.query.get_or_404(team_id)

    # 處理所有隊員與隊長：清除 team_id、變更角色為 visitor
    for member in team.members:
        member.team_id = None
        member.role = "visitor"

    # 如果有指定隊長也處理（避免 null 狀況）
    if team.captain:
        team.captain.team_id = None
        team.captain.role = "visitor"

    db.session.commit()

    # 刪除隊伍
    db.session.delete(team)
    db.session.commit()

    flash(f"隊伍 {team.name} 已刪除，所有成員角色已改為 visitor")
    return redirect(url_for('main.list_users'))

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