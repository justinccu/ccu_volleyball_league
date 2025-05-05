from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, Team
from . import db, bcrypt

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
            flash('❗ 帳號已存在，請使用其他名稱')
            return redirect(url_for('main.register'))
            
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=request.form['username'], password=hashed_pw, role='visitor')
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
        name = request.form['name']  # 👈 一定要有
        role = request.form['role']
        team_id = None

        if User.query.filter_by(username=username).first():
            flash("⚠️ 此帳號已存在")
        else:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

            if role == 'captain':
                new_team_name = request.form.get('new_team_name')
                if not new_team_name:
                    flash("❌ 隊長必須輸入隊伍名稱")
                    return redirect(url_for('main.list_users'))

                # 建立隊伍
                new_team = Team(name=new_team_name)
                db.session.add(new_team)
                db.session.commit()

                # 建立使用者，並指定 team_id
                user = User(username=username, name=name, password=hashed_pw, role=role, team_id=new_team.id)
                db.session.add(user)
                db.session.commit()

                # 補上隊長 ID
                new_team.captain_id = user.id
                db.session.commit()
                flash(f"✅ 已新增隊長 {username} 並建立隊伍 {new_team_name}")

            elif role == 'member':
                team_id = request.form.get('team_id')
                if not team_id:
                    flash("❌ 成員必須選擇隊伍")
                    return redirect(url_for('main.list_users'))

                user = User(username=username, name=name, password=hashed_pw, role=role, team_id=int(team_id))
                db.session.add(user)
                db.session.commit()
                flash(f"✅ 已新增成員 {username} 並加入隊伍")

            elif role == 'visitor':
                user = User(username=username, name=name, password=hashed_pw, role=role)
                db.session.add(user)
                db.session.commit()
                flash(f"✅ 已新增訪客 {username}")

            else:  # admin
                user = User(username=username, name=name, password=hashed_pw, role=role)
                db.session.add(user)
                db.session.commit()
                flash(f"✅ 已新增管理員 {username}")

    users = User.query.all()
    teams = Team.query.all()
    return render_template('list_users.html', users=users, teams=teams)


@main.route('/admin/assign_user', methods=['POST'])
@login_required
def assign_user():
    if current_user.role != 'admin':
        return "❌ 無權限操作", 403

    user_id = request.form.get('user_id')
    team_id = request.form.get('team_id')

    if not user_id or not team_id:
        flash("❌ 請選擇使用者與隊伍")
        return redirect(url_for('main.list_users'))

    user = User.query.get(int(user_id))
    team = Team.query.get(int(team_id))

    if not user or not team:
        flash("❌ 找不到指定使用者或隊伍")
        return redirect(url_for('main.list_users'))

    user.team_id = team.id
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

    flash(f"🗑️ 隊伍 {team.name} 已刪除，所有成員角色已改為 visitor")
    return redirect(url_for('main.list_users'))

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