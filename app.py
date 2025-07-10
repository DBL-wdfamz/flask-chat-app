from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, join_room
import eventlet
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

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

@socketio.on('send_message')
def handle_message(data):
    username = session.get('username', '匿名')
    msg = data['message']
    emit('receive_message', {'username': username, 'message': msg}, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render 会自动设置 PORT
    socketio.run(app, host='0.0.0.0', port=port)
