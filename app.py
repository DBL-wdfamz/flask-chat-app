from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os, re, sqlite3, io

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

# 持久化路径设置：Render 环境设置 DB_PATH=/data/chat.db，默认用本地chat.db
DB_PATH = os.environ.get('DB_PATH', 'chat.db')
UPLOAD_FOLDER = os.environ.get('UPLOAD_PATH', 'static/uploads')
MAX_HISTORY = 100
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_real_ip():
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    return request.remote_addr

def get_conn():
    return sqlite3.connect(DB_PATH)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        ip TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        content TEXT)''')
    c.execute("INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)",
              ('bbstttt', 'wdfamzwdfamz', 1))
    try:
        c.execute("ALTER TABLE users ADD COLUMN ip TEXT")
    except:
        pass  # 已存在忽略
    conn.commit()
    conn.close()

def get_user(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, password, is_admin, ip FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'username': row[0], 'password': row[1], 'is_admin': bool(row[2]), 'ip': row[3]}
    return None

def add_user(username, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

def update_user_ip(username, ip):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET ip = ? WHERE username = ?", (ip, username))
    conn.commit()
    conn.close()

def delete_user_from_db(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, is_admin, ip FROM users")
    users = [{'username': row[0], 'is_admin': bool(row[1]), 'ip': row[2]} for row in c.fetchall()]
    conn.close()
    return users

def save_message(username, content):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM messages")
    total = c.fetchone()[0]
    if total > MAX_HISTORY:
        c.execute("SELECT id, content FROM messages ORDER BY id ASC LIMIT ?", (total - MAX_HISTORY,))
        for row in c.fetchall():
            msg_id, msg_content = row
            if '<img src="' in msg_content:
                match = re.search(r'src=\"(.+?)\"', msg_content)
                if match:
                    img_url = match.group(1)
                    img_path = img_url.replace('/static/', 'static/')
                    try:
                        os.remove(img_path)
                    except:
                        pass
            c.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

def get_messages():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, content FROM messages ORDER BY id ASC")
    messages = [{'username': row[0], 'message': row[1]} for row in c.fetchall()]
    conn.close()
    return messages

@app.route("/aitext")
def aiplugin_response():
    # 从请求中获取参数
    prompt = request.args.get("prompt", default="", type=str)
    
    # 模拟AI响应逻辑
    if prompt:
        reply = f"你输入的是：{prompt}"
    else:
        reply = "请输入 prompt 参数"

    return jsonify({
        "reply": reply
    })

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
            update_user_ip(username, get_real_ip())
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

@app.route('/admin/messages')
def admin_messages():
    if not session.get('is_admin'):
        return "无权限"
    return render_template('admin_messages.html', messages=get_messages())

@app.route('/admin/clear_messages')
def clear_messages():
    if not session.get('is_admin'):
        return "无权限"
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()
    return redirect(url_for('admin_messages'))

@app.route('/admin/download_messages')
def download_messages():
    if not session.get('is_admin'):
        return "无权限"
    messages = get_messages()
    text = "\n".join([f"{m['username']}: {m['message']}" for m in messages])
    return send_file(io.BytesIO(text.encode()), mimetype='text/plain', as_attachment=True, download_name='messages.txt')

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
            'message': f'<img src="{image_url}" style="max-width:200px">'
        }
        save_message(message['username'], message['message'])
        socketio.emit('receive_message', message, broadcast=True)
        return 'OK'
    return 'Invalid file', 400

@socketio.on('connect')
def handle_connect():
    for msg in get_messages():
        emit('receive_message', msg)

@socketio.on('send_message')
def handle_message(data):
    username = session.get('username', '匿名')
    message = {'username': username, 'message': data['message']}
    save_message(username, data['message'])
    emit('receive_message', message, broadcast=True)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db()
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
