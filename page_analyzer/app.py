import os
from datetime import date
from urllib.parse import urlparse

import psycopg2
import requests
import validators
from bs4 import BeautifulSoup
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

    errors = validate_url(url)
    if errors:
        for error in errors:
            flash(error, "danger")
        return render_template("index.html", url=url), 422

    normalized_url = normalize_url(url)

    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id FROM urls WHERE name = %s", (normalized_url,)
                )
                existing = cur.fetchone()

                if existing:
                    flash("Страница уже существует", "info")
                    return redirect(url_for("urls_show", id=existing["id"]))

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
    """Список всех добавленных URL с датой последней проверки"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    u.id, 
                    u.name, 
                    u.created_at,
                    MAX(uc.created_at) as last_check_at
                FROM urls u
                LEFT JOIN url_checks uc ON u.id = uc.url_id
                GROUP BY u.id
                ORDER BY u.id DESC
                """
            )
            urls = cur.fetchall()
    return render_template("urls.html", urls=urls)


@app.route("/urls/<int:id>")
def urls_show(id):
    """Страница конкретного URL со списком проверок"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM urls WHERE id = %s", (id,))
            url = cur.fetchone()

            if not url:
                return render_template("404.html"), 404

            cur.execute(
                """
                SELECT id, status_code, h1, title, description, created_at
                FROM url_checks
                WHERE url_id = %s
                ORDER BY id DESC
                """,
                (id,)
            )
            checks = cur.fetchall()

    return render_template("show.html", url=url, checks=checks)


@app.route("/urls/<int:id>/checks", methods=["POST"])
def checks_create(id):
    """Запускает реальную проверку сайта"""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT name FROM urls WHERE id = %s", (id,))
                url_data = cur.fetchone()
                
                if not url_data:
                    flash("Сайт не найден", "danger")
                    return redirect(url_for("urls_index"))
                
                url = url_data["name"]
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                try:
                    # verify=False - временно для WSL (на Amvera работает без этого)
                    response = requests.get(url, timeout=10, headers=headers, verify=False)
                    status_code = response.status_code
                    
                    if status_code < 400:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        h1_tag = soup.find('h1')
                        h1 = h1_tag.get_text()[:255] if h1_tag else ''
                        
                        title_tag = soup.find('title')
                        title = title_tag.get_text()[:255] if title_tag else ''
                        
                        meta_tag = soup.find('meta', attrs={'name': 'description'})
                        description = meta_tag.get('content', '')[:255] if meta_tag else ''
                        
                        cur.execute(
                            """
                            INSERT INTO url_checks 
                            (url_id, status_code, h1, title, description, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (id, status_code, h1, title, description, date.today())
                        )
                        flash("Страница успешно проверена", "success")
                    else:
                        flash("Произошла ошибка при проверке", "danger")
                        return redirect(url_for("urls_show", id=id))
                    
                except requests.exceptions.RequestException:
                    flash("Произошла ошибка при проверке", "danger")
                    return redirect(url_for("urls_show", id=id))
                
    except Exception:
        flash("Произошла ошибка при проверке", "danger")
    
    return redirect(url_for("urls_show", id=id))