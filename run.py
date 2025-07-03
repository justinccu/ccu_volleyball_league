from app import create_app, db

app = create_app()

with app.app_context():
    db.create_all()
    # 本地測試用
    # app.run(debug=True)