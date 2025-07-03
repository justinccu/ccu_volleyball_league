import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    from .routes import main
    app.register_blueprint(main)

    # -----------------------
    # 建立資料表 & admin 帳號
    # -----------------------
    with app.app_context():
        db.create_all()

        # 匯入 User model（依你的目錄調整）
        from .models import User

        # 檢查是否已存在 admin
        admin_username = 'admin'
        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            pw_hash = bcrypt.generate_password_hash('admin').decode('utf-8')
            admin = User(
                username=admin_username,
                password=pw_hash,
                name='管理員',
                role='admin',
                team_id=None,
                department=None,
                grade=None,
                gender=None,
                student_id=None
            )
            db.session.add(admin)
            db.session.commit()

    return app
