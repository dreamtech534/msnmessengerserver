from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = 'msnmessenger4633'
socketio = SocketIO(app)

USERS_FILE = "users.json"
MESSAGES_FILE = "messages.json"
DM_FILE = "dm_messages.json"
NUDGE_FILE = "nudge_queue.json"


def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

users = load_json(USERS_FILE, {})
messages = load_json(MESSAGES_FILE, [])
dm_messages = load_json(DM_FILE, [])
nudge_queue = load_json(NUDGE_FILE, {})


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    if username in users:
        return jsonify({'status': 'fail', 'reason': 'User exists'}), 409

    users[username] = {
        "password": generate_password_hash(data['password']),
        "status": data.get("status", "Çevrimiçi"),
        "avatar": data.get("avatar", "")
    }

    save_json(USERS_FILE, users)
    add_message("Sunucu", f"{username} sohbete katıldı.")
    return jsonify({'status': 'ok'})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    user = users.get(username)
    if not user or not check_password_hash(user['password'], data['password']):
        return jsonify({'status': 'fail'}), 401
    return jsonify({
        'status': 'ok',
        'user': {
            'username': username,
            'status': user.get('status', 'Çevrimiçi'),
            'avatar': user.get('avatar', '')
        }
    })

@app.route('/send', methods=['POST'])
def send_message():
    data = request.get_json()
    add_message(data['user'], data['text'])
    socketio.emit('new_message', {
        'user': data['user'],
        'text': data['text'],
        'time': timestamp()
    })
    return jsonify({'status': 'ok'})


@app.route('/messages', methods=['GET'])
def get_messages():
    return jsonify(messages)


@app.route('/users', methods=['GET'])
def get_users():
    return jsonify([{"username": u, "status": users[u].get("status", "Çevrimiçi")} for u in users])


@app.route('/dm/send', methods=['POST'])
def send_dm():
    data = request.get_json()
    dm_messages.append({
        "from": data['from'],
        "to": data['to'],
        "text": data['text'],
        "time": timestamp()
    })
    save_json(DM_FILE, dm_messages)
    return jsonify({'status': 'ok'})


@app.route('/dm/<username>', methods=['GET'])
def get_dm(username):
    relevant = [msg for msg in dm_messages if msg['from'] == username or msg['to'] == username]
    return jsonify(relevant)


@app.route('/dm/nudge', methods=['POST'])
def send_nudge():
    data = request.get_json()
    to_user = data['to']
    from_user = data['from']
    if to_user not in nudge_queue:
        nudge_queue[to_user] = []
    nudge_queue[to_user].append({"from": from_user, "time": timestamp()})
    save_json(NUDGE_FILE, nudge_queue)
    return jsonify({'status': 'ok'})


@app.route('/dm/nudge/<username>', methods=['GET'])
def get_nudges(username):
    nudges = nudge_queue.get(username, [])
    nudge_queue[username] = []
    save_json(NUDGE_FILE, nudge_queue)
    return jsonify(nudges)


def add_message(user, text):
    messages.append({"user": user, "text": text, "time": timestamp()})
    if len(messages) > 200:
        messages.pop(0)
    save_json(MESSAGES_FILE, messages)

@socketio.on('new_message')
def handle_new_message(data):
    print(f"New message from {data['user']}: {data['text']}")
    add_message(data['user'], data['text'])
    socketio.emit('new_message', data)

if __name__ == '__main__':
    socketio.run(app, port=5000, debug=True)
