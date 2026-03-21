from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-for-testing')

@app.route("/")
def index():
    print("Hello, World! Page Analyzer is running.")
