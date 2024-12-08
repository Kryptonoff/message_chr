from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from datetime import datetime
import secrets
import random
import json
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Генерация случайного секретного ключа
socketio = SocketIO(app)

# Список неярких цветов
colors = [
    "#6c757d", "#5a6268", "#343a40", "#495057", "#868e96",
    "#adb5bd", "#ced4da", "#dee2e6", "#e9ecef", "#f8f9fa",
    "#f1f3f5", "#e2e6ea", "#d3d9db", "#b0b3b8", "#a6a8ab",
    "#8a8d90", "#7a7d80", "#6c6f72", "#5c5f62", "#4c4f52"
]

# Хранение пользователей и сообщений в памяти
users = {}
messages = []

# Файл для хранения пользователей
users_file = 'users.json'

def load_users():
    """Загрузка пользователей из файла."""
    global users
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)

def save_users():
    """Сохранение пользователей в файл."""
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return render_template('chat.html')

@socketio.on('register')
def handle_register(nickname):
    ip_address = request.remote_addr
    
    if ip_address in users:
        emit('registration_error', {'error': 'Этот IP-адрес уже зарегистрирован с никнеймом: ' + users[ip_address]['nickname']})
    else:
        # Сохраняем никнейм и случайный цвет пользователя по его IP-адресу
        color = random.choice(colors)
        users[ip_address] = {'nickname': nickname, 'color': color}
        save_users()  # Сохраняем пользователей в файл
        emit('registration_success', {'nickname': nickname, 'color': color})
        log_registration(ip_address, nickname)  # Логируем регистрацию

def log_registration(ip_address, nickname):
    """Логирование регистрации пользователя."""
    with open('registration_log.txt', 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.now()}: {nickname} зарегистрирован с IP: {ip_address}\n")

@socketio.on('send_message')
def handle_send_message(data):
    ip_address = request.remote_addr
    user_info = users.get(ip_address, {'nickname': 'Гость', 'color': '#000000'})  # Используем никнейм и цвет по IP или 'Гость'
    nickname = user_info['nickname']
    color = user_info['color']
    message = data['message']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Сохраняем сообщение в памяти
    message_data = {'nickname': nickname, 'message': message, 'timestamp': timestamp, 'color': color}
    messages.append(message_data)
    
    # Отправляем сообщение всем подключенным клиентам
    emit('receive_message', message_data, broadcast=True)

@socketio.on('get_messages')
def handle_get_messages():
    # Отправляем все сообщения клиенту
    emit('all_messages', messages)

if __name__ == '__main__':
    load_users()  # Загружаем пользователей при старте приложения
    socketio.run(app, debug=True)
