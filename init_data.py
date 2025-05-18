from app import create_app, db, bcrypt
from app.models import User, Team

app = create_app()
app.app_context().push()

# 清空舊資料（刪掉所有使用者與隊伍）
db.drop_all()
db.create_all()

# 建立 admin 帳號
admin = User(
    username="admin",
    name="Admin",
    password=bcrypt.generate_password_hash("admin").decode('utf-8'),
    role="admin",
    department="管理單位",
    grade=0,
    gender="不明"
)
db.session.add(admin)
db.session.commit()

# ✅ 男排 + 女排資料
departments = [
    "中文系", "外文系", "資工系", "經濟系", "法律系", "勞工系",
    "會計系", "心理系", "教育系", "社工系", "財政系", "政治系",
    "歐一系","哩ㄎㄧ系", "歌仔系", "我的雞雞好系", "X系", "Y系"
]
grades = [1, 2, 3, 4, 1, 2, 3, 1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3]

# ✅ 男排隊伍 captainA ~ captainL
for i in range(18):
    dept = departments[i]
    username = f"captain{chr(65 + i)}"           # A~L
    name = f"金 {chr(65 + i)}"
    plain_pw = "0000"
    grade = grades[i]

    team = Team(name=dept, captain_id=None, team_type="男排")
    db.session.add(team)
    db.session.commit()

    captain = User(
        username=username,
        name=name,
        password=bcrypt.generate_password_hash(plain_pw).decode('utf-8'),
        role="captain",
        team_id=team.id,
        department=dept,
        grade=grade,
        gender="男"
    )
    db.session.add(captain)
    db.session.commit()

    team.captain_id = captain.id
    db.session.commit()

# ✅ 女排隊伍 captainM ~ captainX
for i in range(18):
    dept = departments[i]
    username = f"captain{chr(77 + i)}"           # M~X
    name = f"林 {chr(77 + i)}"
    plain_pw = "0"
    grade = grades[i]

    team = Team(name=dept, captain_id=None, team_type="女排")
    db.session.add(team)
    db.session.commit()

    captain = User(
        username=username,
        name=name,
        password=bcrypt.generate_password_hash(plain_pw).decode('utf-8'),
        role="captain",
        team_id=team.id,
        department=dept,
        grade=grade,
        gender="女"
    )
    db.session.add(captain)
    db.session.commit()

    team.captain_id = captain.id
    db.session.commit()

print("✅ 已建立 12 男排 + 12 女排 隊伍與隊長（帳號 captainA~X, 密碼 0)")
print("✅ 已建立管理員帳號:admin / admin")
