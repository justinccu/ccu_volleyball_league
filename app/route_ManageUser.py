from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import User, Team, Match, JoinRequest
from . import db, bcrypt
from .config import departments

route_ManageUser = Blueprint('route_ManageUser', __name__)

# 管理使用者（admin）=> 新增 + 顯示 + 篩選
@route_ManageUser.route('/admin/users', methods=['GET', 'POST'])
@login_required
def list_users():
    if current_user.role != 'admin':
        return "❌ 無權限查看使用者列表", 403

    # 處理新增
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        role = request.form['role']
        team_type = request.form.get('team_type')
        department = request.form.get('department')
        grade = int(request.form.get('grade', 0))
        gender = request.form.get('gender')
        team_id = None

        if User.query.filter_by(username=username).first():
            flash("⚠️ 此帳號已存在")
        else:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

            if role == 'captain':
                new_team_name = request.form.get('new_team_name')
                if not new_team_name:
                    flash("❌ 隊長必須輸入隊伍名稱")
                    return redirect(url_for('route_ManageUser.list_users'))

                existing_team = Team.query.filter_by(name=new_team_name, team_type=team_type).first()
                if existing_team:
                    flash("❌ 該隊伍名稱已被使用，請選擇其他名稱")
                    return redirect(url_for('route_ManageUser.list_users'))

                # 建立隊伍
                new_team = Team(name=new_team_name, team_type=team_type)
                db.session.add(new_team)
                db.session.commit()

                # 建立使用者，並指定 team_id
                user = User(
                    username=username, name=name, password=hashed_pw, role=role,
                    team_id=new_team.id, department=department, grade=grade, gender=gender
                )
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
                    return redirect(url_for('route_ManageUser.list_users'))

                user = User(
                    username=username, name=name, password=hashed_pw, role=role,
                    team_id=int(team_id), department=department, grade=grade, gender=gender
                )
                db.session.add(user)
                db.session.commit()
                flash(f"已新增成員 {username} 並加入隊伍")

            elif role == 'visitor':
                user = User(
                    username=username, name=name, password=hashed_pw, role=role,
                    department=department, grade=grade, gender=gender
                )
                db.session.add(user)
                db.session.commit()
                flash(f"已新增訪客 {username}")

            else:  # admin
                department = "管理單位"
                grade = 0
                gender = "不明"
                user = User(
                    username=username, name=name, password=hashed_pw, role=role,
                    department=department, grade=grade, gender=gender
                )
                db.session.add(user)
                db.session.commit()
                flash(f"已新增管理員 {username}")

    # 篩選處理 (GET 參數)
    team_type = request.args.get('team_type')
    team_id = request.args.get('team_id')

    # 全部隊伍
    teams = Team.query.order_by(Team.team_type, Team.name).all()

    # 動態篩選
    query = User.query
    if team_type:
        team_ids = [t.id for t in teams if t.team_type == team_type]
        query = query.filter(User.team_id.in_(team_ids))
    if team_id:
        query = query.filter(User.team_id == int(team_id))
    users = query.all()
  
    return render_template(
        'list_users.html',
        users=users,
        teams=teams,
        departments=departments,
        team_type=team_type,
        team_id=team_id
    )


@route_ManageUser.route('/admin/assign_user', methods=['POST'])
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
    return redirect(url_for('route_ManageUser.list_users'))

# 刪除使用者（admin）
@route_ManageUser.route('/admin/delete_user/<int:user_id>', methods=['POST'])
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
    return redirect(url_for('route_ManageUser.list_users'))

@route_ManageUser.route('/admin/delete_team/<int:team_id>', methods=['POST'])
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
    return redirect(url_for('route_ManageUser.list_users'))