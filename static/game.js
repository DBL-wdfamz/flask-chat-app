const socket = io();
let keys = {};

window.addEventListener('keydown', function(e) {
    keys[e.keyCode] = true;
    socket.emit('player_action', { keyCode: e.keyCode });
});

window.addEventListener('keyup', function(e) {
    keys[e.keyCode] = false;
});

socket.on('enemy_action', function(data) {
    // 模拟对方玩家按键（这里只是示例，具体需绑定动作）
    simulateRemotePlayer(data.keyCode);
});

function simulateRemotePlayer(keyCode) {
    // 示例：按键映射到 player2 的行为
    // 需要替换为实际游戏逻辑
    if (keyCode === 65) movePlayer2Left();
    if (keyCode === 68) movePlayer2Right();
}

function movePlayer2Left() {
    const pl2 = document.getElementById('player2');
    pl2.style.left = (pl2.offsetLeft - 10) + 'px';
}

function movePlayer2Right() {
    const pl2 = document.getElementById('player2');
    pl2.style.left = (pl2.offsetLeft + 10) + 'px';
}
