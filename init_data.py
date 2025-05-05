# init_data.py

from app import create_app, db, bcrypt
from app.models import User, Team

app = create_app()
app.app_context().push()

# 清空舊資料（⚠️ 會刪掉所有使用者與隊伍）
db.drop_all()
db.create_all()

# 建立隊伍與隊長帳號
for i in range(10):
    team_name = f"Team {chr(65 + i)}"           # Team A ~ Team J
    username = f"captain{chr(65 + i)}"          # captainA ~ captainJ
    name = f"金 {chr(65 + i)}"             # Captain A ~ Captain J
    plain_pw = "0000"

    # 建立隊伍（先不指定隊長）
    team = Team(name=team_name, captain_id=None)
    db.session.add(team)
    db.session.commit()

    # 建立隊長帳號，綁定 team_id
    hashed_pw = bcrypt.generate_password_hash(plain_pw).decode('utf-8')
    captain = User(
        username=username,
        name=name,
        password=hashed_pw,
        role="captain",
        team_id=team.id
    )
    db.session.add(captain)
    db.session.commit()

    # 設定隊伍的 captain_id
    team.captain_id = captain.id
    db.session.commit()

# 建立 admin 帳號
admin_username = "admin"
admin_password = "admin"
admin_name = "Admin"
hashed_admin_pw = bcrypt.generate_password_hash(admin_password).decode('utf-8')
admin = User(
    username=admin_username,
    name=admin_name,
    password=hashed_admin_pw,
    role="admin"
)
db.session.add(admin)
db.session.commit()

print("✅ 已建立 10 隊與 10 位隊長（帳號 captainA ~ captainJ, 密碼 0000)")
print("✅ 已建立管理員帳號:admin / admin")
