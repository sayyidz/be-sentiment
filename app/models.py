# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Wisata(db.Model):
    __tablename__ = 'wisata'
    
    id = db.Column(db.Integer, primary_key=True)
    nama_wisata = db.Column(db.String(150), nullable=False)
    jumlah_ulasan = db.Column(db.Integer, nullable=False)
    link_file = db.Column(db.String(255), nullable=False)
