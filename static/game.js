const socket = io();
let keys = {};

const player1 = document.getElementById('player1');
const player2 = document.getElementById('player2');

window.addEventListener('keydown', function(e) {
    keys[e.keyCode] = true;

    // 控制本地 player1
    handleLocalKey(e.keyCode);

    // 发给对方
    socket.emit('player_action', { keyCode: e.keyCode });
});

window.addEventListener('keyup', function(e) {
    keys[e.keyCode] = false;
});

// 处理自己按键
function handleLocalKey(keyCode) {
    if (keyCode === 37 || keyCode === 65) movePlayer1Left();
    if (keyCode === 39 || keyCode === 68) movePlayer1Right();
}

function movePlayer1Left() {
    player1.style.left = (player1.offsetLeft - 10) + 'px';
}

function movePlayer1Right() {
    player1.style.left = (player1.offsetLeft + 10) + 'px';
}

// 接收远程动作并控制 player2
socket.on('enemy_action', function(data) {
    simulateRemotePlayer(data.keyCode);
});

function simulateRemotePlayer(keyCode) {
    if (keyCode === 37 || keyCode === 65) movePlayer2Left();
    if (keyCode === 39 || keyCode === 68) movePlayer2Right();
}

function movePlayer2Left() {
    player2.style.left = (player2.offsetLeft - 10) + 'px';
}

function movePlayer2Right() {
    player2.style.left = (player2.offsetLeft + 10) + 'px';
}
