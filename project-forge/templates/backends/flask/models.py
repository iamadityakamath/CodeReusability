from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class ProjectMeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    author = db.Column(db.String(100), nullable=False)
