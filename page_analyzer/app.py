import os
from datetime import date
from urllib.parse import urlparse

import psycopg2
import validators
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-for-testing")
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Создаёт подключение к базе данных"""
    return psycopg2.connect(DATABASE_URL)


def normalize_url(url):
    """Нормализует URL: оставляет только схему и домен"""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def validate_url(url):
    """Проверяет URL на корректность"""
    errors = []
    if not url:
        errors.append("URL обязателен")
    elif len(url) > 255:
        errors.append("URL превышает 255 символов")
    elif not validators.url(url):
        errors.append("Некорректный URL")
    return errors


@app.route("/")
def index():
    """Главная страница"""
    return render_template("index.html")


@app.route("/urls", methods=["POST"])
def urls_create():
    """Добавляет новый URL в базу данных"""
    url = request.form.get("url", "")

    # Валидация
    errors = validate_url(url)
    if errors:
        for error in errors:
            flash(error, "danger")
        return render_template("index.html", url=url), 422

    # Нормализация URL
    normalized_url = normalize_url(url)

    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Проверяем, существует ли уже такой URL
                cur.execute(
                    "SELECT id FROM urls WHERE name = %s", (normalized_url,)
                )
                existing = cur.fetchone()

                if existing:
                    flash("Страница уже существует", "info")
                    return redirect(url_for("urls_show", id=existing["id"]))

                # Добавляем новый URL
                cur.execute(
                    "INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id",
                    (normalized_url, date.today()),
                )
                new_id = cur.fetchone()["id"]
                flash("Страница успешно добавлена", "success")
                return redirect(url_for("urls_show", id=new_id))

    except Exception as e:
        flash(f"Ошибка базы данных: {str(e)}", "danger")
        return render_template("index.html", url=url), 500


@app.route("/urls")
def urls_index():
    """Список всех добавленных URL"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, created_at
                FROM urls
                ORDER BY id DESC
                """
            )
            urls = cur.fetchall()
    return render_template("urls.html", urls=urls)


@app.route("/urls/<int:id>")
def urls_show(id):
    """Страница конкретного URL"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM urls WHERE id = %s", (id,))
            url = cur.fetchone()

            if not url:
                return render_template("404.html"), 404

    return render_template("show.html", url=url, checks=[])