from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

# 模拟用户数据库（仅在内存中）
users = {
    'admin': {'password': 'admin123', 'is_admin': True}  # 默认管理员账户
}

chat_history = []
MAX_HISTORY = 100

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)
        if user and user['password'] == password:
            session['username'] = username
            session['is_admin'] = user.get('is_admin', False)
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error="用户名或密码错误")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return render_template('register.html', error="用户名已存在")
        users[username] = {'password': password, 'is_admin': False}
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', username=session['username'])

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return "无权限访问"
    return render_template('admin.html', users=users)

@app.route('/delete_user/<username>')
def delete_user(username):
    if not session.get('is_admin'):
        return "无权限操作"
    if username != 'admin':
        users.pop(username, None)
    return redirect(url_for('admin'))

@socketio.on('connect')
def handle_connect():
    for msg in chat_history:
        emit('receive_message', msg)

@socketio.on('send_message')
def handle_message(data):
    username = session.get('username', '匿名')
    message = {'username': username, 'message': data['message']}
    chat_history.append(message)
    if len(chat_history) > MAX_HISTORY:
        chat_history.pop(0)
    emit('receive_message', message, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
