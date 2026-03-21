import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-for-testing')

@app.route('/')
def index():
    print("Hello, World! Page Analyzer is running.")  # это уйдёт в логи
    return "Hello, World! Page Analyzer is running."  # это увидит браузер