from flask import Flask, render_template, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length
import secrets
from datetime import datetime, timedelta
import time

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Генерация случайного секретного ключа
socketio = SocketIO(app)

# Список для хранения сообщений с временными метками
messages = []

# Определение формы для ввода ника
class NicknameForm(FlaskForm):
    nickname = StringField('Введите ваш ник:', validators=[DataRequired(), Length(min=1, max=20)])
    submit = SubmitField('Подтвердить')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = NicknameForm()
    if form.validate_on_submit():
        session['nickname'] = form.nickname.data  # Сохраняем ник в сессии
        flash(f'Ваш ник: {session["nickname"]}', 'success')  # Сообщение об успехе
        return redirect(url_for('chat'))  # Перенаправление на страницу чата

    return render_template('index.html', form=form)

@app.route('/chat')
def chat():
    if 'nickname' not in session:
        return redirect(url_for('index'))  # Если ника нет, перенаправляем на главную страницу
    return render_template('chat.html', nickname=session['nickname'])

@socketio.on('send_message')
def handle_send_message(data):
    # Добавляем временную метку к сообщению
    timestamped_message = {
        'nickname': data['nickname'],
        'message': data['message'],
        'timestamp': datetime.now()
    }
    messages.append(timestamped_message)  # Сохраняем сообщение
    emit('receive_message', timestamped_message, broadcast=True)  # Отправляем сообщение всем клиентам

    # Отправляем все текущие сообщения клиенту
    emit('all_messages', messages, broadcast=True)

def cleanup_old_messages():
    global messages
    one_hour_ago = datetime.now() - timedelta(hours=1)
    messages = [msg for msg in messages if msg['timestamp'] > one_hour_ago]  # Оставляем только свежие сообщения

def background_cleanup():
    while True:
        cleanup_old_messages()
        time.sleep(60)  # Запускаем очистку каждую минуту

# Запускаем фоновую задачу для очистки старых сообщений
socketio.start_background_task(background_cleanup)

if __name__ == '__main__':
    socketio.run(app, host='193.168.46.53', port=5000)  # Укажите нужный IP и порт
