from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

chat_history = []  # 全局消息记录
MAX_HISTORY = 100  # 最多保存100条消息


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            session['username'] = username
            return redirect(url_for('chat'))
    return render_template('login.html')


@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', username=session['username'])


@socketio.on('connect')
def handle_connect():
    # 每个新用户连接时，发送历史聊天记录
    for msg in chat_history:
        emit('receive_message', msg)


@socketio.on('send_message')
def handle_message(data):
    username = session.get('username', '匿名')
    message = {'username': username, 'message': data['message']}

    # 保存到历史记录
    chat_history.append(message)
    if len(chat_history) > MAX_HISTORY:
        chat_history.pop(0)  # 删除最早的一条

    # 广播给所有连接用户
    emit('receive_message', message, broadcast=True)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
