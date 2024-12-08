from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_socketio import SocketIO, emit
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
import secrets
from datetime import datetime
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
socketio = SocketIO(app)

# Настройки MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'chr_chat'
mysql = MySQL(app)

@app.route('/')
def home():
    return redirect(url_for('login'))

# Определение массива цветов
COLORS = [
    '#FFB3BA', '#FFDFBA', '#FFFABA', '#BAFFC9', '#BAE1FF',
    '#FFC3A0', '#FF677D', '#D4A5A5', '#392F5A', '#F9AFAF',
    '#F6F6D7', '#D9BF77', '#A8D8EA', '#FFE156', '#6A0572'
]

# Определение формы для регистрации
class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=1, max=20)])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

# Определение формы для входа
class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = generate_password_hash(form.password.data)  # Хешируем пароль
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        mysql.connection.commit()
        cur.close()
        flash('Вы успешно зарегистрировались!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user[2], password):  # user[2] - это хеш пароля
            session['username'] = user[1]  # user[1] - это имя пользователя
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('username', None)  # Удаляем пользователя из сессии
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('login'))

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))  # Если пользователя нет в сессии, перенаправляем на страницу входа
    
    # Выбираем случайный цвет
    user_color = random.choice(COLORS)
    session['user_color'] = user_color  # Сохраняем цвет в сессии
    
    return render_template('chat.html', username=session['username'], user_color=user_color)

@socketio.on('send_message')
def handle_send_message(data):
    nickname = data['nickname']
    message = data['message']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_color = session.get('user_color', '#000000')  # Получаем цвет пользователя, если он есть
    
    # Сохраняем сообщение в базе данных
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO messages (nickname, message, timestamp) VALUES (%s, %s, %s)", (nickname, message,    timestamp))
    mysql.connection.commit()
    message_id = cur.lastrowid  # Получаем ID последнего вставленного сообщения
    cur.close()
    
    # Отправляем сообщение всем подключенным клиентам
    emit('receive_message', {'id': message_id, 'nickname': nickname, 'message': message, 'timestamp': timestamp, 'color': user_color}, broadcast=True)

@socketio.on('get_messages')
def handle_get_messages():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nickname, message, timestamp FROM messages ORDER BY timestamp ASC")
    messages = cur.fetchall()
    cur.close()
    
    # Форматируем сообщения для отправки
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            'id': msg[0],
            'nickname': msg[1],
            'message': msg[2],
            'timestamp': msg[3].strftime('%Y-%m-%d %H:%M:%S')  # Преобразуем datetime в строку
        })
    
    # Отправляем все сообщения клиенту
    emit('all_messages', formatted_messages)

@socketio.on('delete_message')
def handle_delete_message(data):
    message_id = data['id']
    
    # Получаем сообщение из базы данных, чтобы проверить автора
    cur = mysql.connection.cursor()
    cur.execute("SELECT nickname FROM messages WHERE id = %s", (message_id,))
    message = cur.fetchone()
    
    if message:
        nickname = message[0]
        # Проверяем, является ли текущий пользователь автором сообщения
        if nickname == session['username']:
            # Удаляем сообщение из базы данных
            cur.execute("DELETE FROM messages WHERE id = %s", (message_id,))
            mysql.connection.commit()
            emit('message_deleted', {'id': message_id}, broadcast=True)
        else:
            # Если пользователь не автор, отправляем сообщение об ошибке
            emit('error', {'message': 'Вы не можете удалить это сообщение.'}, room=request.sid)
    cur.close()

if __name__ == '__main__':
    socketio.run(app, debug=True)
    socketio.run(app, host='193.168.46.53', port=5000, debug=True)