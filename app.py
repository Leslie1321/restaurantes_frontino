from flask import Flask, render_template, request, redirect, session, flash, url_for
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "clave_secreta"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# -----------------------------
# CREAR BASE DE DATOS SI NO EXISTE
# -----------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS restaurantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            direccion TEXT,
            telefono TEXT,
            foto TEXT
        )
    """)

    # Crear admin por defecto
    c.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (username, password, role) VALUES ('admin', 'admin', 'admin')")

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        # ⬅ CAMBIO IMPORTANTE
        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM usuarios WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("index"))
        else:
            flash("Credenciales incorrectas")

    return render_template("login.html")


# -----------------------------
# CERRAR SESIÓN
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------------
# INICIO + BÚSQUEDA
# -----------------------------
@app.route("/")
def index():
    q = request.args.get("q", "")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if q:
        c.execute("""
            SELECT * FROM restaurantes
            WHERE nombre LIKE ? OR direccion LIKE ? OR telefono LIKE ?
        """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    else:
        c.execute("SELECT * FROM restaurantes")

    restaurantes = c.fetchall()
    conn.close()

    return render_template(
        "index.html",
        restaurantes=restaurantes,
        search=q,
        current_user=session.get("user"),
        current_role=session.get("role")
    )


# -----------------------------
# FORMULARIO PARA AGREGAR
# -----------------------------
@app.route("/add_form")
def add_form():
    if session.get("role") != "admin":
        flash("No tienes permisos")
        return redirect(url_for("index"))
    return render_template("add.html")


# -----------------------------
# GUARDAR RESTAURANTE
# -----------------------------
@app.route("/add", methods=["POST"])
def add():
    if session.get("role") != "admin":
        flash("No tienes permisos")
        return redirect(url_for("index"))

    nombre = request.form["nombre"]
    direccion = request.form["direccion"]
    telefono = request.form["telefono"]

    foto = None
    if "foto" in request.files:
        file = request.files["foto"]
        if file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            foto = filename

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO restaurantes (nombre, direccion, telefono, foto) VALUES (?, ?, ?, ?)",
              (nombre, direccion, telefono, foto))
    conn.commit()
    conn.close()

    flash("Restaurante agregado correctamente")
    return redirect(url_for("index"))


# -----------------------------
# EDITAR RESTAURANTE
# -----------------------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if session.get("role") != "admin":
        flash("No tienes permisos")
        return redirect(url_for("index"))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        direccion = request.form["direccion"]
        telefono = request.form["telefono"]

        foto = request.form.get("foto_actual")

        if "foto" in request.files:
            file = request.files["foto"]
            if file.filename != "":
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                foto = filename

        c.execute("""
            UPDATE restaurantes
            SET nombre=?, direccion=?, telefono=?, foto=?
            WHERE id=?
        """, (nombre, direccion, telefono, foto, id))

        conn.commit()
        conn.close()

        flash("Restaurante actualizado")
        return redirect(url_for("index"))

    c.execute("SELECT * FROM restaurantes WHERE id=?", (id,))
    restaurante = c.fetchone()
    conn.close()

    return render_template("edit.html", r=restaurante)


# -----------------------------
# ELIMINAR
# -----------------------------
@app.route("/delete/<int:id>")
def delete(id):
    if session.get("role") != "admin":
        flash("No tienes permisos")
        return redirect(url_for("index"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM restaurantes WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("Restaurante eliminado")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        try:
            c.execute("INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'user')",
                      (username, password))
            conn.commit()
            flash("Usuario registrado correctamente")
            return redirect(url_for("login"))
        except:
            flash("El usuario ya existe")

        conn.close()

    return render_template("register.html")


# -----------------------------
# INICIO DEL SERVIDOR
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
