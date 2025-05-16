from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, Team, Match, JoinRequest
from . import db, bcrypt
from itertools import combinations
import random
from datetime import datetime, timedelta
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
        return redirect(url_for('main.login'))
    return render_template('register.html')

# 顯示抽籤頁面
@main.route('/admin/draw_teams', methods=['GET'])
@login_required
def show_draw_teams_page():
    if current_user.role != 'admin':
        flash("❌ 無權限操作")
        return redirect(url_for('main.dashboard'))
    
    # 從 URL 參數獲取 team_type
    team_type = request.args.get('team_type')
    
    # 如果有 team_type，重新查詢分組資訊
    if team_type:
        group_a_teams = Team.query.filter_by(team_type=team_type, team_cycle='A').order_by(Team.name).all()
        group_b_teams = Team.query.filter_by(team_type=team_type, team_cycle='B').order_by(Team.name).all()
        return render_template('draw_teams.html', 
                             team_type=team_type,
                             group_a=group_a_teams,
                             group_b=group_b_teams)
    
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

        # 清除所有比賽記錄
        try:
            Match.query.delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"清除比賽記錄時發生錯誤：{str(e)}")
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

@main.route('/admin/generate_schedule', methods=['POST'])
@login_required
def generate_schedule():
    if current_user.role != 'admin':
        flash("❌ 無權限操作")
        return redirect(url_for('main.draw_teams', team_type=request.form.get('team_type')))

    team_type = request.form.get('team_type')
    group_a = request.form.getlist('group_a')
    group_b = request.form.getlist('group_b')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    if not team_type or not group_a or not group_b:
        flash("❌ 缺少必要資訊：請確保已選擇隊伍類型並完成分組")
        return redirect(url_for('main.draw_teams', team_type=team_type))

    if not start_date_str or not end_date_str:
        flash("❌ 請選擇比賽開始和結束日期")
        return redirect(url_for('main.draw_teams', team_type=team_type))

    try:
        Match.query.delete()
        db.session.commit()
        # 驗證日期格式
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        if start_date > end_date:
            flash("❌ 開始日期不能晚於結束日期")
            return redirect(url_for('main.draw_teams', team_type=team_type))

        # 計算每個隊伍擔任裁判的次數
        def get_referee_counts(teams):
            referee_counts = {}
            for team in teams:
                count = Match.query.filter_by(referee_id=team.id).count()
                referee_counts[team.id] = count
            return referee_counts

        # 生成可用的比賽時間
        def generate_available_times():
            available_times = []
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() in {0, 1, 3, 4}:  # 週一、二、四、五
                    for hour in range(19, 24):
                        match_time = datetime(
                            current_date.year,
                            current_date.month,
                            current_date.day,
                            hour
                        )
                        available_times.append(match_time)
                current_date += timedelta(days=1)
            return available_times

        # 為每個分組生成循環賽賽程
        def generate_group_schedule(teams, other_group_teams, used_times):
            schedule = []
            # 獲取另一組隊伍的裁判次數
            referee_counts = get_referee_counts(other_group_teams)
            
            # 獲取所有可用的時間
            all_available_times = generate_available_times()
            # 過濾掉已使用的時間
            available_times = [t for t in all_available_times if t not in used_times]
            
            required_matches = len(list(combinations(teams, 2)))
            if len(available_times) < required_matches:
                flash(f"❌ 可用的比賽時間不足")
                return [], used_times
            
            time_index = 0
            
            for team1, team2 in combinations(teams, 2):
                # 找出另一組中擔任裁判次數最少的隊伍
                min_count = min(referee_counts.values())
                available_referees = [team for team in other_group_teams 
                                    if referee_counts[team.id] == min_count]
                referee = random.choice(available_referees)
                
                # 更新裁判次數
                referee_counts[referee.id] += 1
                
                # 獲取隊伍 ID
                team1_obj = Team.query.filter_by(name=team1, team_type=team_type).first()
                team2_obj = Team.query.filter_by(name=team2, team_type=team_type).first()
                referee_obj = referee

                if not team1_obj or not team2_obj:
                    flash(f"❌ 找不到隊伍：{team1 if not team1_obj else team2}")
                    return [], used_times

                # 檢查是否已存在相同的比賽
                existing_match = Match.query.filter(
                    ((Match.team1_id == team1_obj.id) & (Match.team2_id == team2_obj.id)) |
                    ((Match.team1_id == team2_obj.id) & (Match.team2_id == team1_obj.id))
                ).first()

                if not existing_match:
                    # 建立比賽
                    match = Match(
                        team1_id=team1_obj.id,
                        team2_id=team2_obj.id,
                        referee_id=referee_obj.id,
                        match_time=available_times[time_index]
                    )
                    used_times.add(available_times[time_index])
                    time_index += 1
                    schedule.append(match)

            return schedule, used_times

        # 獲取隊伍對象
        group_a_teams = [Team.query.filter_by(name=name, team_type=team_type).first() for name in group_a]
        group_b_teams = [Team.query.filter_by(name=name, team_type=team_type).first() for name in group_b]

        # 用於追蹤已使用的時間
        used_times = set()

        # 生成 A 組和 B 組的賽程
        schedule_a, used_times = generate_group_schedule(group_a, group_b_teams, used_times)
        if not schedule_a:
            return redirect(url_for('main.draw_teams', team_type=team_type))
            
        schedule_b, used_times = generate_group_schedule(group_b, group_a_teams, used_times)
        if not schedule_b:
            return redirect(url_for('main.draw_teams', team_type=team_type))

        # 將所有比賽保存到資料庫
        for match in schedule_a + schedule_b:
            db.session.add(match)
        db.session.commit()

        # 重新查詢分組資訊以顯示在頁面上
        group_a_teams = Team.query.filter_by(team_type=team_type, team_cycle='A').order_by(Team.name).all()
        group_b_teams = Team.query.filter_by(team_type=team_type, team_cycle='B').order_by(Team.name).all()

        # 查詢所有新生成的比賽
        matches = Match.query.filter(
            Match.team1.has(team_type=team_type)
        ).order_by(Match.match_time).all()

        flash("✅ 賽程已成功生成")
        return render_template('draw_teams.html', 
                             team_type=team_type, 
                             group_a=group_a_teams, 
                             group_b=group_b_teams,
                             matches=matches)
    except ValueError as e:
        flash(f"❌ 日期格式錯誤：{str(e)}")
        return redirect(url_for('main.draw_teams', team_type=team_type))
    except Exception as e:
        db.session.rollback()
        flash(f"❌ 生成賽程時發生錯誤：{str(e)}")
        return redirect(url_for('main.draw_teams', team_type=team_type))

@main.route('/team/list')
@login_required
def list_teams():
    teams = Team.query.all()
    return render_template('list_team.html', teams=teams)

@main.route('/my/matches')
@login_required
def my_matches():
    if current_user.role not in ['captain', 'member']:
        return "❌ 僅限隊長與隊員查看", 403

    team = current_user.team
    if not team:
        return render_template('my_matches.html', team=None, matches=[])

    matches = Match.query.filter(
        (Match.team1_id == team.id) | (Match.team2_id == team.id)
    ).all()

    return render_template('my_matches.html', team=team, matches=matches)

@main.route('/join/request', methods=['GET', 'POST'])
@login_required
def join_request():
    if current_user.team_id:
        flash("你已經加入隊伍")
        return redirect(url_for('main.dashboard'))

    pending_request = JoinRequest.query.filter_by(user_id=current_user.id, status='pending').first()

    if request.method == 'POST' and not pending_request:
        team_id = request.form['team_id']
        jr = JoinRequest(user_id=current_user.id, team_id=team_id)
        db.session.add(jr)
        db.session.commit()
        flash("已送出申請，請等待隊長審核")
        return redirect(url_for('main.join_request'))

    teams = Team.query.all()
    return render_template('join_team_request.html', teams=teams, pending_request=pending_request)

@main.route('/captain/requests')
@login_required
def view_join_requests():
    if current_user.role != 'captain' or not current_user.team:
        return "❌ 僅限隊長操作", 403
    team = current_user.team
    requests = JoinRequest.query.filter_by(team_id=team.id, status='pending').all()
    return render_template('approve_join_request.html', requests=requests)

@main.route('/captain/approve/<int:request_id>', methods=['POST'])
@login_required
def approve_join(request_id):
    req = JoinRequest.query.get_or_404(request_id)
    if current_user.id != req.team.captain_id:
        return "❌ 僅限該隊隊長審核", 403

    req.status = 'approved'
    req.user.team_id = req.team_id
    req.user.role = 'member'
    db.session.commit()
    flash(f"✅ {req.user.name} 已加入 {req.team.name}")
    return redirect(url_for('main.view_join_requests'))

@main.route('/captain/reject/<int:request_id>', methods=['POST'])
@login_required
def reject_join(request_id):
    req = JoinRequest.query.get_or_404(request_id)
    if current_user.id != req.team.captain_id:
        return "❌ 僅限該隊隊長審核", 403

    req.status = 'rejected'
    db.session.commit()
    flash(f"❌ 已拒絕 {req.user.name} 的申請")
    return redirect(url_for('main.view_join_requests'))

@main.route('/my/team_members')
@login_required
def team_members():
    if current_user.team is None:
        flash("❌ 你尚未加入任何隊伍")
        return redirect(url_for('main.dashboard'))
    return render_template('team_members.html', team=current_user.team)

@main.route('/referee/submit_result/<int:match_id>', methods=['GET', 'POST'])
@login_required
def submit_match_result(match_id):
    match = Match.query.get_or_404(match_id)

    # 僅允許裁判隊伍的隊長操作
    if current_user.role != 'captain' or not current_user.team or match.referee_id != current_user.team.id:
        return "❌ 僅裁判隊伍之隊長可登錄比賽成績", 403

    if request.method == 'POST':
        team1_set1 = int(request.form['team1_set1'])
        team2_set1 = int(request.form['team2_set1'])
        team1_set2 = int(request.form['team1_set2'])
        team2_set2 = int(request.form['team2_set2'])
        team1_set3 = request.form.get('team1_set3')
        team2_set3 = request.form.get('team2_set3')
        team1_lamp = int(request.form['team1_lamp_fee'])
        team2_lamp = int(request.form['team2_lamp_fee'])

        # 設定分數
        match.team1_set1 = team1_set1
        match.team2_set1 = team2_set1
        match.team1_set2 = team1_set2
        match.team2_set2 = team2_set2
        match.team1_set3 = int(team1_set3) if team1_set3 else None
        match.team2_set3 = int(team2_set3) if team2_set3 else None
        match.team1_lamp_fee = team1_lamp
        match.team2_lamp_fee = team2_lamp

        # 自動計算勝負
        team1_win = 0
        team2_win = 0
        if team1_set1 > team2_set1:
            team1_win += 1
        else:
            team2_win += 1

        if team1_set2 > team2_set2:
            team1_win += 1
        else:
            team2_win += 1

        if team1_win == 1 and team2_win == 1:
            if team1_set3 is not None and team2_set3 is not None:
                if int(team1_set3) > int(team2_set3):
                    team1_win += 1
                else:
                    team2_win += 1
            else:
                flash("⚠️ 前兩局打平，請補第三局成績")
                return redirect(request.url)

        if team1_win > team2_win:
            match.winner_id = match.team1_id
            match.loser_id = match.team2_id
        else:
            match.winner_id = match.team2_id
            match.loser_id = match.team1_id

        match.status = 'waiting_confirm'
        match.team1_confirmed = False
        match.team2_confirmed = False
        match.result_submitted_by = current_user.id

        db.session.commit()
        flash("✅ 成績已成功登錄，等待雙方確認")
        return redirect(url_for('main.referee_matches'))

    return render_template('submit_match_result.html', match=match)

@main.route('/match/confirm/<int:match_id>', methods=['POST'])
@login_required
def confirm_match(match_id):
    match = Match.query.get_or_404(match_id)
    team = current_user.team

    # ✅ 僅限比賽雙方隊伍的「隊長」可以操作
    if (
        current_user.role != 'captain' or
        not team or
        team.id not in [match.team1_id, match.team2_id]
    ):
        return "❌ 僅限參賽隊伍的隊長可操作", 403

    # 更新該隊的確認狀態
    if team.id == match.team1_id:
        match.team1_confirmed = True
    elif team.id == match.team2_id:
        match.team2_confirmed = True

    # 若兩隊皆已確認，則標記為 confirmed
    if match.team1_confirmed and match.team2_confirmed:
        match.status = 'confirmed'

    db.session.commit()
    flash("✅ 你已確認比賽結果")
    return redirect(url_for('main.my_matches'))

@main.route('/match/reject/<int:match_id>', methods=['POST'])
@login_required
def reject_match(match_id):
    match = Match.query.get_or_404(match_id)
    team = current_user.team

    if (
        current_user.role != 'captain' or
        not team or
        team.id not in [match.team1_id, match.team2_id]
    ):
        return "❌ 僅限參賽隊伍的隊長可操作", 403

    match.status = 'rejected'
    match.team1_confirmed = False
    match.team2_confirmed = False
    db.session.commit()
    flash("❌ 你已拒絕此比賽結果，請裁判重新登錄")
    return redirect(url_for('main.my_matches'))

@main.route('/referee/matches')
@login_required
def referee_matches():
    if current_user.role != 'captain' or not current_user.team:
        return "❌ 僅限隊長操作", 403

    # 顯示所有由該隊伍擔任裁判的比賽，不論狀態
    matches = Match.query.filter(
        Match.referee_id == current_user.team.id
    ).order_by(Match.match_time.desc().nullslast()).all()

    return render_template('referee_match_list.html', matches=matches)

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