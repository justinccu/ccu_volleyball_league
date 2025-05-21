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

# 男/女排資料
departments = [
    "中文系", "外文系", "資工系", "經濟系", "法律系", "勞工系",
    "會計系", "心理系", "教育系", "社工系", "財政系", "政治系",
    "歐一系", "哩ㄎㄧ系", "歌仔系", "我的雞雞好系", "X系", "Y系"
]
grades = [1, 2, 3, 4, 1, 2, 3, 1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3]

# 男排隊伍 m_captainA ~ m_captainR 並新增一位隊員
for i in range(len(departments)):
    dept = departments[i]
    username = f"m_captain{chr(65 + i)}"   # m_captainA ~ m_captainR
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

    # 新增一位男隊員
    member_username = f"m_member{chr(65 + i)}"
    member_name = f"王 {chr(65 + i)}"
    member = User(
        username=member_username,
        name=member_name,
        password=bcrypt.generate_password_hash(plain_pw).decode('utf-8'),
        role="member",
        team_id=team.id,
        department=dept,
        grade=grade,
        gender="男"
    )
    db.session.add(member)
    db.session.commit()

# 女排隊伍 f_captainA ~ f_captainR 並新增一位隊員
for i in range(len(departments)):
    dept = departments[i]
    username = f"f_captain{chr(65 + i)}"   # f_captainA ~ f_captainR
    name = f"林 {chr(65 + i)}"
    plain_pw = "0000"
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

    # 新增一位女隊員
    member_username = f"f_member{chr(65 + i)}"
    member_name = f"陳 {chr(65 + i)}"
    member = User(
        username=member_username,
        name=member_name,
        password=bcrypt.generate_password_hash(plain_pw).decode('utf-8'),
        role="member",
        team_id=team.id,
        department=dept,
        grade=grade,
        gender="女"
    )
    db.session.add(member)
    db.session.commit()

print(f"✅ 已建立 {len(departments)} 男排 + {len(departments)} 女排 隊伍與隊長(帳號 m_captainA~R / f_captainA~R, 密碼 0000), 每隊也新增一位隊員(帳號 m_memberA~R / f_memberA~R, 密碼 0000)")
print("✅ 已建立管理員帳號: admin / admin")
