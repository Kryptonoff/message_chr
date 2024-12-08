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

# Список ярких цветов
colors = [
    "#FF5733", "#FFBD33", "#DBFF33", "#75FF33", "#33FF57",
    "#33FFBD", "#33DBFF", "#3375FF", "#3357FF", "#5733FF",
    "#BD33FF", "#FF33DB", "#FF3375", "#FF33B5", "#FF33A1",
    "#FF6F33", "#FF9F33", "#FFCC33", "#FFEB33", "#FF33A8"
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
        emit('registration_error', {'error': 'Вы уже зарегистрированы с ником: ' + users[ip_address]['nickname']})
    else:
        # Сохраняем никнейм и случайный цвет пользователя по его IP-адресу
        color = random.choice(colors)
        print(f"Выбранный цвет для {nickname}: {color}")  # Отладочное сообщение
        users[ip_address] = {'nickname': nickname, 'color': color, 'nickname_changes': 0}
        save_users()  # Сохраняем пользователей в файл
        emit('registration_success', {'nickname': nickname, 'color': color})
        log_registration(ip_address, nickname)  # Логируем регистрацию

@socketio.on('change_nickname')
def handle_change_nickname(new_nickname):
    ip_address = request.remote_addr
    
    if ip_address in users:
        if users[ip_address]['nickname_changes'] < 3:
            users[ip_address]['nickname'] = new_nickname
            users[ip_address]['nickname_changes'] += 1
            save_users()  # Сохраняем пользователей в файл
            remaining_attempts = 3 - users[ip_address]['nickname_changes']  # Вычисляем оставшиеся попытки
            emit('nickname_changed', {'nickname': new_nickname, 'remaining_attempts': remaining_attempts})
        else:
            emit('registration_error', {'error': 'Вы достигли максимального количества смен ника.'})
    else:
        emit('registration_error', {'error': 'Сначала зарегистрируйтесь.'})

def log_registration(ip_address, nickname):
    """Логирование регистрации пользователя."""
    with open('registration_log.txt', 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.now()}: {nickname} зарегистрирован с IP: {ip_address}\n")

@socketio.on('get_current_nickname')
def handle_get_current_nickname():
    ip_address = request.remote_addr
    if ip_address in users:
        nickname = users[ip_address]['nickname']
        emit('current_nickname', {'nickname': nickname})
    else:
        emit('current_nickname', {'nickname': 'Не установлен'})

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
    load_users()  # Загружаем пользователей при старте
    socketio.run(app, host='localhost', port=5000, debug=True)
