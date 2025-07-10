from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os, re

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

# 用户数据库（可替换为 SQLite）
users = {
    'bbstttt': {'password': 'wdfamzwdfamz', 'is_admin': True}
}

chat_history = []
MAX_HISTORY = 100

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def delete_oldest_message():
    old_msg = chat_history.pop(0)
    if '<img src="' in old_msg['message']:
        match = re.search(r'src=\"(.+?)\"', old_msg['message'])
        if match:
            img_url = match.group(1)
            img_path = img_url.replace('/static/', 'static/')
            try:
                os.remove(img_path)
                print(f"🧹 删除过期图片: {img_path}")
            except Exception as e:
                print(f"⚠️ 删除图片失败: {e}")

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
        return "无权限"
    return render_template('admin.html', users=users)

@app.route('/delete_user/<username>')
def delete_user(username):
    if not session.get('is_admin'):
        return "无权限"
    if username != 'admin':
        users.pop(username, None)
    return redirect(url_for('admin'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files or 'username' not in session:
        return 'No image uploaded', 400
    file = request.files['image']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        image_url = url_for('static', filename='uploads/' + filename)
        message = {
            'username': session['username'],
            'message': f'<img src=\"{image_url}\" style=\"max-width:200px\">'
        }
        chat_history.append(message)
        if len(chat_history) > MAX_HISTORY:
            delete_oldest_message()
        socketio.emit('receive_message', message, broadcast=True)
        return 'OK'
    return 'Invalid file', 400

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
        delete_oldest_message()
    emit('receive_message', message, broadcast=True)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
