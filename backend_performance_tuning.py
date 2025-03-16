import time
import threading
import logging
from functools import wraps
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from redis import Redis
import psycopg2
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dbname')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
redis = Redis(host='localhost', port=6379)

# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String, nullable=False)
    user = db.relationship('User', backref=db.backref('posts', lazy=True))

# Performance metrics decorator
def performance_metrics(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logging.info(f"Execution time for {func.__name__}: {execution_time:.4f} seconds")
        return result
    return wrapper

# Caching decorator
def cache_result(timeout=60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args):
            cache_key = f"{func.__name__}:{args}"
            cached_result = redis.get(cache_key)
            if cached_result:
                logging.info(f"Cache hit for {func.__name__} with args {args}")
                return cached_result
            logging.info(f"Cache miss for {func.__name__} with args {args}, computing result...")
            result = func(*args)
            redis.setex(cache_key, timeout, result)
            return result
        return wrapper
    return decorator

# Asynchronous processing example
def long_running_task(user_id):
    logging.info(f"Starting long-running task for user {user_id}")
    time.sleep(10)  # Simulate a long task
    logging.info(f"Completed long-running task for user {user_id}")

@app.route('/users', methods=['GET'])
@performance_metrics
def get_users():
    users = User.query.all()
    return jsonify([{'id': user.id, 'username': user.username, 'email': user.email} for user in users])

@app.route('/posts', methods=['GET'])
@performance_metrics
@cache_result(timeout=120)
def get_posts():
    posts = Post.query.all()
    return jsonify([{'id': post.id, 'user_id': post.user_id, 'content': post.content} for post in posts])

@app.route('/add_user', methods=['POST'])
@performance_metrics
def add_user():
    username = request.json.get('username')
    email = request.json.get('email')
    new_user = User(username=username, email=email)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User added'}), 201

@app.route('/add_post', methods=['POST'])
@performance_metrics
def add_post():
    user_id = request.json.get('user_id')
    content = request.json.get('content')
    new_post = Post(user_id=user_id, content=content)
    db.session.add(new_post)
    db.session.commit()
    threading.Thread(target=long_running_task, args=(user_id,)).start()
    return jsonify({'message': 'Post added'}), 201

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)