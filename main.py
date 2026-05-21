from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import random

app = Flask(__name__)
CORS(app)

DATABASE = "database.db"


def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        email TEXT,
        password TEXT,
        bio TEXT DEFAULT '',
        coins INTEGER DEFAULT 100,
        clicks INTEGER DEFAULT 0,
        chaos_level INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        item_name TEXT,
        emoji TEXT,
        rarity TEXT
    )
    """)

    conn.commit()
    conn.close()


ITEMS = [
    {"name": "Caos", "emoji": "🌀", "rarity": "common", "chance": 50},
    {"name": "Fuego", "emoji": "🔥", "rarity": "rare", "chance": 25},
    {"name": "Alien", "emoji": "👽", "rarity": "epic", "chance": 15},
    {"name": "Rey", "emoji": "👑", "rarity": "legendary", "chance": 8},
    {"name": "TUNG", "emoji": "⚡", "rarity": "mythic", "chance": 2},
]


def roll():

    r = random.randint(1, 100)

    total = 0

    for item in ITEMS:

        total += item["chance"]

        if r <= total:
            return item

    return ITEMS[0]


@app.route("/signup", methods=["POST"])
def signup():

    data = request.json

    username = data["username"]
    email = data["email"]
    password = generate_password_hash(data["password"])

    conn = db()
    cur = conn.cursor()

    exists = cur.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    ).fetchone()

    if exists:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Usuario ya existe"
        })

    cur.execute("""
    INSERT INTO users(username,email,password)
    VALUES(?,?,?)
    """, (username, email, password))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Cuenta creada"
    })


@app.route("/login", methods=["POST"])
def login():

    data = request.json

    username = data["username"]
    password = data["password"]

    conn = db()
    cur = conn.cursor()

    user = cur.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    ).fetchone()

    conn.close()

    if not user:
        return jsonify({
            "success": False,
            "message": "Usuario no existe"
        })

    if not check_password_hash(user["password"], password):
        return jsonify({
            "success": False,
            "message": "Contraseña incorrecta"
        })

    return jsonify({
        "success": True,
        "user": {
            "username": user["username"],
            "coins": user["coins"],
            "clicks": user["clicks"],
            "chaos_level": user["chaos_level"]
        }
    })


@app.route("/click", methods=["POST"])
def click():

    data = request.json
    username = data["username"]

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    UPDATE users
    SET
        clicks = clicks + 1,
        coins = coins + 1
    WHERE username=?
    """, (username,))

    cur.execute("""
    UPDATE users
    SET chaos_level = (clicks / 10) + 1
    WHERE username=?
    """, (username,))

    conn.commit()

    user = cur.execute("""
    SELECT *
    FROM users
    WHERE username=?
    """, (username,)).fetchone()

    conn.close()

    return jsonify({
        "success": True,
        "coins": user["coins"],
        "clicks": user["clicks"],
        "chaos_level": int(user["chaos_level"])
    })


@app.route("/gacha/pull", methods=["POST"])
def gacha():

    data = request.json

    username = data["username"]
    cost = data["cost"]

    conn = db()
    cur = conn.cursor()

    user = cur.execute("""
    SELECT *
    FROM users
    WHERE username=?
    """, (username,)).fetchone()

    if user["coins"] < cost:

        conn.close()

        return jsonify({
            "success": False,
            "message": "No tienes suficientes coins"
        })

    item = roll()

    cur.execute("""
    UPDATE users
    SET coins = coins - ?
    WHERE username=?
    """, (cost, username))

    cur.execute("""
    INSERT INTO inventory(
        username,
        item_name,
        emoji,
        rarity
    )
    VALUES(?,?,?,?)
    """, (
        username,
        item["name"],
        item["emoji"],
        item["rarity"]
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "item": item
    })


@app.route("/profile/<username>")
def profile(username):

    conn = db()
    cur = conn.cursor()

    user = cur.execute("""
    SELECT *
    FROM users
    WHERE username=?
    """, (username,)).fetchone()

    inventory = cur.execute("""
    SELECT *
    FROM inventory
    WHERE username=?
    """, (username,)).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "profile": {
            "username": user["username"],
            "bio": user["bio"],
            "coins": user["coins"],
            "clicks": user["clicks"],
            "chaos_level": user["chaos_level"],
            "inventory": [dict(i) for i in inventory]
        }
    })


@app.route("/profile/update", methods=["POST"])
def update_profile():

    data = request.json

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    UPDATE users
    SET bio=?
    WHERE username=?
    """, (
        data["bio"],
        data["username"]
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


@app.route("/leaderboard")
def leaderboard():

    conn = db()
    cur = conn.cursor()

    users = cur.execute("""
    SELECT username, chaos_level, clicks, coins
    FROM users
    ORDER BY chaos_level DESC
    LIMIT 10
    """).fetchall()

    conn.close()

    return jsonify({
        "leaderboard": [dict(u) for u in users]
    })


@app.route("/chaos-quote")
def quote():

    quotes = [
        "TUNG TUNG SAHUR",
        "Tu cerebro colapsó",
        "El caos es eterno",
        "Las neuronas murieron",
        "Todo es TUNG"
    ]

    return jsonify({
        "quote": random.choice(quotes)
    })


if __name__ == "__main__":

    init_db()

    app.run(debug=True)