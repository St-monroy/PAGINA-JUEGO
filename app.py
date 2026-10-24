import os, sqlite3, secrets
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "ssrcm.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SSRCM_SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

GAMES = [
 {"id":"moon","name":"AETERNUM - BLADES","studio":"SSRCM Indie","category":"Acción y aventura","image":"aeternum-cover.jpg","screenshots":["blades-gameplay-1.png","blades-gameplay-2.png","blades-gameplay-3.png","blades-gameplay-4.png"],"rating":4.8,"downloads":"En desarrollo","size":"Por definir","badge":"JUEGO DESTACADO","itch_url":"https://steven03.itch.io/aeternum-blades","description":"Un antiguo reino cubierto por la oscuridad. Enfrenta entidades y poderosos jefes para restaurar la paz perdida."},
 {"id":"farm","name":"Curse of Forest","studio":"SSRCM Indie","category":"Aventura","image":"curse-forest-cover.png","screenshots":["curse-forest-gameplay-2.png","curse-forest-gameplay-3.png","curse-forest-gameplay-4.png"],"rating":4.7,"downloads":"En desarrollo","size":"Por definir","badge":"AVENTURA INDIE","itch_url":"https://ssrcm-studio.itch.io/the-curse-of-the-forest-demo","description":"Adéntrate en un bosque misterioso, descubre sus secretos y explora un mundo lleno de rincones por descubrir."},
 {"id":"neon","name":"Chemistry","studio":"SSRCM Indie","category":"Puzles","image":"chemistry-cover.png","screenshots":["chemistry-question.png","chemistry-periodic-table.png","chemistry-victory.png","chemistry-loading.png"],"rating":4.6,"downloads":"En desarrollo","size":"Por definir","badge":"NUEVO PROYECTO","itch_url":"https://sebbb22.itch.io/chemistry-demo-v001","description":"Una experiencia diferente que combina curiosidad, exploración y desafíos por resolver."},
]

def connect_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    with connect_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL COLLATE NOCASE UNIQUE,
          email TEXT NOT NULL COLLATE NOCASE UNIQUE,
          password_hash TEXT NOT NULL,
          bio TEXT NOT NULL DEFAULT '',
          avatar TEXT NOT NULL DEFAULT '🎮',
          role TEXT NOT NULL DEFAULT 'player',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS favorites (
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          game_id TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(user_id, game_id)
        );
        CREATE TABLE IF NOT EXISTS reviews (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          game_id TEXT NOT NULL,
          rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
          body TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS posts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          body TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # Optional first admin: set SSRCM_ADMIN_USER and SSRCM_ADMIN_PASSWORD before starting.
        admin_user, admin_pass = os.environ.get("SSRCM_ADMIN_USER"), os.environ.get("SSRCM_ADMIN_PASSWORD")
        if admin_user and admin_pass:
            found = db.execute("SELECT id FROM users WHERE username=?", (admin_user,)).fetchone()
            if not found:
                db.execute("INSERT INTO users(username,email,password_hash,role) VALUES(?,?,?,?)",
                    (admin_user, os.environ.get("SSRCM_ADMIN_EMAIL", "admin@ssrcm.local"), generate_password_hash(admin_pass), "admin"))

init_db()

@app.before_request
def load_user():
    g.user = None
    uid = session.get("user_id")
    if uid:
        g.user = connect_db().execute("SELECT id, username, email, bio, avatar, role, created_at FROM users WHERE id=?", (uid,)).fetchone()

@app.context_processor
def globals_for_templates():
    return {"current_user": g.get("user"), "year": datetime.now().year}

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not g.user:
            flash("Inicia sesión para usar esta función.", "info")
            return redirect(url_for("auth", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not g.user or g.user["role"] != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

def find_game(game_id):
    return next((game for game in GAMES if game["id"] == game_id), None)

def user_favorites(user_id):
    with connect_db() as db:
        return {r["game_id"] for r in db.execute("SELECT game_id FROM favorites WHERE user_id=?", (user_id,))}

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "Todos")
    view = request.args.get("view", "Descubrir")
    games = GAMES[:]
    if q:
        games = [x for x in games if q.casefold() in (x["name"]+" "+x["studio"]+" "+x["category"]).casefold()]
    if category != "Todos":
        games = [x for x in games if x["category"] == category]
    favorites = user_favorites(g.user["id"]) if g.user else set()
    if view in ("Favoritos", "Mi biblioteca"):
        games = [x for x in games if x["id"] in favorites]
    elif view == "Novedades":
        games = [x for x in games if x["id"] in ("neon", "world")]
    elif view == "Top juegos":
        games.sort(key=lambda x: x["rating"], reverse=True)
    return render_template("index.html", games=games, all_games=GAMES, favorites=favorites, q=q, category=category, view=view,
        categories=["Todos","Aventura","RPG","Arcade","Simulación","Acción","Puzles"])

@app.route("/game/<game_id>")
def game_detail(game_id):
    game = find_game(game_id)
    if not game: abort(404)
    with connect_db() as db:
        reviews = db.execute("""SELECT reviews.*, users.username, users.avatar FROM reviews
          JOIN users ON users.id=reviews.user_id WHERE game_id=? ORDER BY reviews.id DESC""", (game_id,)).fetchall()
        avg = db.execute("SELECT AVG(rating) AS avg, COUNT(*) AS n FROM reviews WHERE game_id=?", (game_id,)).fetchone()
    favorites = user_favorites(g.user["id"]) if g.user else set()
    return render_template("juego.html", game=game, reviews=reviews, avg=avg["avg"], review_count=avg["n"], is_favorite=game_id in favorites)

@app.route("/auth", methods=["GET","POST"])
def auth():
    if g.user: return redirect(url_for("profile"))
    if request.method == "POST":
        action = request.form.get("action", "login")
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        with connect_db() as db:
            if action == "register":
                email = request.form.get("email","").strip().lower()
                if len(username) < 3 or len(username) > 24 or not username.replace("_","").isalnum():
                    flash("El usuario debe tener 3–24 caracteres: letras, números o guion bajo.", "error")
                elif len(password) < 8:
                    flash("La contraseña debe tener al menos 8 caracteres.", "error")
                elif "@" not in email or len(email) > 160:
                    flash("Escribe un correo válido.", "error")
                else:
                    try:
                        cur = db.execute("INSERT INTO users(username,email,password_hash) VALUES(?,?,?)",
                            (username,email,generate_password_hash(password)))
                        session.clear(); session["user_id"] = cur.lastrowid
                        flash("¡Cuenta creada! Bienvenido a SSRCM.", "success")
                        return redirect(url_for("profile"))
                    except sqlite3.IntegrityError:
                        flash("Ese usuario o correo ya está registrado.", "error")
            else:
                user = db.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
                if user and check_password_hash(user["password_hash"], password):
                    session.clear(); session["user_id"] = user["id"]
                    flash("Sesión iniciada correctamente.", "success")
                    return redirect(request.args.get("next") or url_for("index"))
                flash("Usuario o contraseña incorrectos.", "error")
    return render_template("acceso.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear(); flash("Has cerrado sesión.", "info")
    return redirect(url_for("index"))

@app.route("/favorite/<game_id>", methods=["POST"])
@login_required
def toggle_favorite(game_id):
    if not find_game(game_id): abort(404)
    with connect_db() as db:
        row = db.execute("SELECT 1 FROM favorites WHERE user_id=? AND game_id=?", (g.user["id"],game_id)).fetchone()
        if row:
            db.execute("DELETE FROM favorites WHERE user_id=? AND game_id=?", (g.user["id"],game_id))
            flash("Juego eliminado de tu biblioteca.", "info")
        else:
            db.execute("INSERT OR IGNORE INTO favorites(user_id,game_id) VALUES(?,?)", (g.user["id"],game_id))
            flash("Juego guardado en tu biblioteca.", "success")
    return redirect(request.referrer or url_for("index"))

@app.route("/review/<game_id>", methods=["POST"])
@login_required
def add_review(game_id):
    if not find_game(game_id): abort(404)
    body = request.form.get("body","").strip()
    try: rating = int(request.form.get("rating","5"))
    except ValueError: rating = 0
    if not 1 <= rating <= 5 or len(body) < 3 or len(body) > 800:
        flash("La reseña debe tener entre 3 y 800 caracteres y una valoración de 1 a 5.", "error")
    else:
        with connect_db() as db:
            db.execute("INSERT INTO reviews(user_id,game_id,rating,body) VALUES(?,?,?,?)", (g.user["id"],game_id,rating,body))
        flash("¡Gracias por compartir tu opinión!", "success")
    return redirect(url_for("game_detail", game_id=game_id)+"#reviews")

@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        bio = request.form.get("bio","").strip()[:240]
        avatar = request.form.get("avatar","🎮")[:12]
        if len(username) < 3 or len(username) > 24 or not username.replace("_","").isalnum():
            flash("El usuario debe tener 3–24 caracteres y usar letras, números o guion bajo.", "error")
        else:
            try:
                with connect_db() as db:
                    db.execute("UPDATE users SET username=?, bio=?, avatar=? WHERE id=?", (username,bio,avatar,g.user["id"]))
                flash("Perfil actualizado.", "success")
                return redirect(url_for("profile"))
            except sqlite3.IntegrityError:
                flash("Ese nombre de usuario ya existe.", "error")
    favorites = user_favorites(g.user["id"])
    with connect_db() as db:
        reviews = db.execute("SELECT * FROM reviews WHERE user_id=? ORDER BY id DESC", (g.user["id"],)).fetchall()
    return render_template("perfil.html", favorites=favorites, games=GAMES, reviews=reviews)

@app.route("/api/asistente", methods=["POST"])
def assistant_reply():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip().lower()[:500]
    if not message:
        return jsonify({"reply": "¡Escríbeme algo! Puedo hacerte preguntas de química, contarte sobre los juegos o ayudarte a usar SSRCM."}), 400

    # Respuestas cortas al reto de química que Pixel propone.
    if message.strip(" .!¡?¿") in ("b", "b)", "la b", "opción b", "opcion b"):
        reply = "¡Correcto! 🎉 El símbolo del oxígeno es O. El oxígeno tiene número atómico 8. ¿Listo para otra pregunta? Escribe ‘otra pregunta de Chemistry’."
    elif message.strip(" .!¡?¿") in ("a", "a)", "la a", "c", "c)", "la c"):
        reply = "Casi 😄 La respuesta correcta era B) O, el símbolo químico del oxígeno. ¡Vamos con otra! Escribe ‘hazme otra pregunta de Chemistry’."
    # Chemistry es un juego de preguntas de química: Pixel también puede practicar con el jugador.
    elif any(word in message for word in ("chemistry", "química", "quimica", "pregunta de química", "preguntas de quimica", "juego de química", "juego de quimica")):
        if any(word in message for word in ("pregunta", "quiz", "reto", "practicar", "jugar", "hazme", "ponme", "pregúntame", "preguntame")):
            reply = "¡Vamos con un reto de Chemistry! 🧪\n\nPregunta: ¿Cuál es el símbolo químico del oxígeno?\nA) Ox\nB) O\nC) Og\n\nRespóndeme A, B o C y seguimos con otra pregunta de química."
        elif any(word in message for word in ("respuesta", "es la b", "opción b", "opcion b", "b)")):
            reply = "¡Correcto! 🎉 El símbolo del oxígeno es O. El oxígeno tiene número atómico 8. ¿Listo para otra pregunta? Escribe ‘otra pregunta de Chemistry’."
        elif any(word in message for word in ("elemento", "tabla periódica", "tabla periodica", "átomo", "atomo", "símbolo", "simbolo")):
            reply = "En Chemistry puedes practicar conceptos como elementos, símbolos químicos, átomos y tabla periódica 🧪. Por ejemplo, H es hidrógeno, O es oxígeno y Na es sodio. Si quieres jugar, pídeme una pregunta de química."
        else:
            reply = "Chemistry es un juego de preguntas de química 🧪. Su objetivo es poner a prueba lo que sabes de elementos, símbolos, tabla periódica y conceptos químicos. Pixel también puede hacerte preguntas para practicar: escribe ‘hazme una pregunta de Chemistry’."
    elif any(word in message for word in ("blades", "aeternum", "guerrero", "caballero", "acción", "accion", "jefe", "mazmorra")):
        reply = "AETERNUM - BLADES ⚔️ es una aventura de acción y fantasía con estética pixel art. Exploras un reino oscuro, recorres mazmorras y te enfrentas a criaturas y enemigos. Las capturas del slider muestran al guerrero en distintas zonas del juego."
    elif any(word in message for word in ("curse", "forest", "bosque", "miedo", "misterio", "terror", "psicológico", "psicologico", "susto")):
        reply = "The Curse of Forest 🌲 es un juego de terror psicológico. Su experiencia se centra en la tensión, el misterio, la exploración y sucesos inquietantes que hacen dudar de lo que está ocurriendo. Si te gusta una historia oscura que te haga pensar, este juego es para ti."
    elif any(word in message for word in ("recomienda", "recomendación", "recomendacion", "qué juego", "que juego", "cuál juego", "cual juego", "jugar")):
        reply = "¡Depende de tu estilo! ⚔️ AETERNUM - BLADES es acción y aventura; 🧪 Chemistry es un juego de preguntas de química; 🌲 The Curse of Forest es terror psicológico. ¿Cuál quieres conocer mejor?"
    elif any(word in message for word in ("favorito", "biblioteca", "guardar")):
        reply = "Puedes guardar juegos en Favoritos o en Mi biblioteca desde las tarjetas del catálogo. Para conservarlos asociados a tu cuenta, primero inicia sesión."
    elif any(word in message for word in ("cuenta", "registr", "iniciar sesión", "iniciar sesion", "perfil")):
        reply = "En SSRCM puedes crear una cuenta o entrar desde el botón ‘Entrar’. Con tu cuenta puedes configurar tu perfil, guardar favoritos y participar en la comunidad."
    elif any(word in message for word in ("comunidad", "jugadores", "reseña", "resena", "opinar")):
        reply = "En la sección Jugadores puedes conocer a la comunidad y compartir publicaciones. En la ficha de cada juego puedes consultar y escribir reseñas después de iniciar sesión."
    elif any(word in message for word in ("hola", "buenas", "hey", "holi")):
        reply = "¡Hey, jugador! 👾 Soy Pixel, el asistente de SSRCM. Puedo recomendarte juegos, hacerte preguntas de química de Chemistry o contarte sobre el terror psicológico de The Curse of Forest."
    elif any(word in message for word in ("ayuda", "qué haces", "que haces", "qué puedes", "que puedes", "ssrcm", "página", "pagina")):
        reply = "Soy Pixel, el asistente de SSRCM 👾. Puedo hablarte de AETERNUM - BLADES, hacerte preguntas de química de Chemistry, explicarte The Curse of Forest y ayudarte con favoritos, perfiles y comunidad. Prueba: ‘hazme una pregunta de Chemistry’."
    else:
        reply = "Puedo ayudarte con los tres juegos de SSRCM: AETERNUM - BLADES (acción y aventura), Chemistry (preguntas de química) y The Curse of Forest (terror psicológico). También puedo explicarte cómo guardar favoritos o participar en la comunidad. ¿Qué quieres descubrir?"
    return jsonify({"reply": reply})


@app.route("/players")
def players():
    with connect_db() as db:
        people = db.execute("SELECT id,username,bio,avatar,created_at FROM users ORDER BY id DESC LIMIT 100").fetchall()
        posts = db.execute("""SELECT posts.id, posts.body, posts.created_at, users.username, users.avatar
            FROM posts JOIN users ON users.id=posts.user_id ORDER BY posts.id DESC LIMIT 30""").fetchall()
    return render_template("comunidad.html", people=people, posts=posts)

@app.route("/community/post", methods=["POST"])
@login_required
def community_post():
    body = request.form.get("body","").strip()
    if len(body) < 3 or len(body) > 500:
        flash("La publicación debe tener entre 3 y 500 caracteres.", "error")
    else:
        with connect_db() as db:
            db.execute("INSERT INTO posts(user_id,body) VALUES(?,?)", (g.user["id"],body))
        flash("Publicación compartida.", "success")
    return redirect(url_for("players")+"#community")

@app.route("/admin")
@admin_required
def admin():
    with connect_db() as db:
        users = db.execute("SELECT id,username,email,role,created_at FROM users ORDER BY id DESC").fetchall()
        reviews = db.execute("""SELECT reviews.id,reviews.game_id,reviews.rating,reviews.body,reviews.created_at,users.username
          FROM reviews JOIN users ON users.id=reviews.user_id ORDER BY reviews.id DESC LIMIT 30""").fetchall()
        post_count = db.execute("SELECT COUNT(*) AS n FROM posts").fetchone()["n"]
    return render_template("panel.html", users=users, reviews=reviews, post_count=post_count)

@app.route("/admin/user/<int:user_id>/role", methods=["POST"])
@admin_required
def admin_role(user_id):
    role = request.form.get("role","player")
    if role not in ("player","admin"): abort(400)
    if user_id == g.user["id"] and role != "admin":
        flash("No puedes quitarte tu propio rol de administrador.", "error")
    else:
        with connect_db() as db:
            db.execute("UPDATE users SET role=? WHERE id=?", (role,user_id))
        flash("Rol actualizado.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete(user_id):
    if user_id == g.user["id"]:
        flash("No puedes eliminar tu propia cuenta desde el panel.", "error")
    else:
        with connect_db() as db: db.execute("DELETE FROM users WHERE id=?", (user_id,))
        flash("Usuario eliminado.", "success")
    return redirect(url_for("admin"))

@app.errorhandler(403)
def forbidden(_): return render_template("error.html", code=403, message="No tienes permiso para acceder a esta sección."), 403
@app.errorhandler(404)
def missing(_): return render_template("error.html", code=404, message="No encontramos esa página o juego."), 404

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
