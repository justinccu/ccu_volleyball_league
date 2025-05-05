# init_data.py

from app import create_app, db, bcrypt
from app.models import User, Team

app = create_app()
app.app_context().push()

# 清空舊資料（刪掉所有使用者與隊伍）
db.drop_all()
db.create_all()

# 建立 admin 帳號
admin_username = "admin"
admin_password = "admin"
admin_name = "Admin"
hashed_admin_pw = bcrypt.generate_password_hash(admin_password).decode('utf-8')
admin = User(
    username=admin_username,
    name=admin_name,
    password=hashed_admin_pw,
    role="admin",
    department="管理單位",
    grade=0,
    gender="不明"
)
db.session.add(admin)
db.session.commit()

# 建立 5 個男排隊伍與隊長
departments = ["中文系", "外文系", "資工系", "經濟系", "法律系", "勞工系"]
genders = ["男"] * 6  # 全部男
grades = [1, 2, 3, 4, 1, 2]

for i in range(6):
    department = departments[i]
    team_name = department                  # 隊伍名稱 = 科系名稱
    username = f"captain{chr(65 + i)}"      # captainA ~ captainE
    name = f"金 {chr(65 + i)}"               # 金 A ~ 金 E
    plain_pw = "0000"
    gender = genders[i]
    grade = grades[i]

    # 建立隊伍（指定為男排，先不設定隊長）
    team = Team(name=team_name, captain_id=None, team_type="男排")
    db.session.add(team)
    db.session.commit()

    # 建立隊長帳號
    hashed_pw = bcrypt.generate_password_hash(plain_pw).decode('utf-8')
    captain = User(
        username=username,
        name=name,
        password=hashed_pw,
        role="captain",
        team_id=team.id,
        department=department,
        grade=grade,
        gender=gender
    )
    db.session.add(captain)
    db.session.commit()

    # 設定隊伍的 captain_id
    team.captain_id = captain.id
    db.session.commit()

print("✅ 已建立 6 隊男排隊伍與 6 位男隊長（帳號 captainA ~ captainF, 密碼 0000)")
print("✅ 已建立管理員帳號:admin / admin")