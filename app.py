from flask import Flask, render_template, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Генерация случайного секретного ключа
socketio = SocketIO(app)

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
    emit('receive_message', data, broadcast=True)  # Отправляем сообщение всем подключенным клиентам

if __name__ == '__main__':
    socketio.run(app, host='193.168.46.53', port=5000)  # Укажите нужный IP и порт
