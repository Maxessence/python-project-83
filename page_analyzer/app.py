import os

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-for-testing")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/urls", methods=["POST"])
def urls_create():
    # Временная заглушка — просто перенаправляем на главную
    flash("Функция добавления URL скоро появится", "info")
    return redirect(url_for("index"))