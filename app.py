from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os, re, sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

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
            except Exception as e:
                print(f"删除图片失败: {e}")

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0)''')
    # 默认管理员账号
    c.execute("INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)",
              ('admin', 'admin123', 1))
    conn.commit()
    conn.close()

def get_user(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username, password, is_admin FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'username': row[0], 'password': row[1], 'is_admin': bool(row[2])}
    return None

def add_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

def delete_user_from_db(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username, is_admin FROM users")
    users = [{'username': row[0], 'is_admin': bool(row[1])} for row in c.fetchall()]
    conn.close()
    return users

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user(username)
        if user and user['password'] == password:
            session['username'] = username
            session['is_admin'] = user['is_admin']
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error="用户名或密码错误")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if get_user(username):
            return render_template('register.html', error="用户名已存在")
        add_user(username, password)
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
    return render_template('admin.html', users=get_all_users())

@app.route('/delete_user/<username>')
def delete_user(username):
    if not session.get('is_admin'):
        return "无权限"
    if username != 'admin':
        delete_user_from_db(username)
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
    init_db()
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
