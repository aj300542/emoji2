// ======= 快照管理 =======
let historyStates = [];
let currentHistoryIndex = -1;
let isRestoring = false;

function recordCanvasState() {
    if (isRestoring) return;

    const snapshot = elements.map(el => {
        if (!el) return null;
        return {
            x: el.x,
            y: el.y,
            rotation: el.rotation,
            scale: el.scale,
            size: el.size
        };
    });

    if (currentHistoryIndex < historyStates.length - 1) {
        historyStates = historyStates.slice(0, currentHistoryIndex + 1);
    }

    historyStates.push(snapshot);
    currentHistoryIndex++;
    console.log(`📸 已记录状态：索引 ${currentHistoryIndex}`);
}

function restoreCanvasFromState(index) {
    if (index < 0 || index >= historyStates.length) {
        console.warn("⚠️ 无效索引，无法恢复");
        return;
    }

    isRestoring = true;
    const snapshot = historyStates[index];

    elements.forEach((el, i) => {
        const snap = snapshot[i];
        if (!snap) {
            console.warn(`⚠️ 快照缺失：索引 ${i}`);
            return;
        }
        el.x = snap.x;
        el.y = snap.y;
        el.rotation = snap.rotation;
        el.scale = snap.scale;
        el.size = snap.size;
    });


    drawAll();
    currentHistoryIndex = index;
    isRestoring = false;
    console.log(`🔁 已恢复状态，索引： ${index}`);
}

function undoCanvasState() {
    if (currentHistoryIndex <= 0) {
        console.warn("⚠️ 没有可撤销的状态");
        return;
    }
    restoreCanvasFromState(currentHistoryIndex - 1);
    console.log(`⏪ 撤销至索引 ${currentHistoryIndex}`);
}

function redoCanvasState() {
    if (currentHistoryIndex >= historyStates.length - 1) {
        console.warn("⚠️ 没有可重做的状态");
        return;
    }
    restoreCanvasFromState(currentHistoryIndex + 1);
    console.log(`⏩ 重做至索引 ${currentHistoryIndex}`);
}

// ======= 快捷键监听 =======
document.addEventListener('keydown', (e) => {
    const tag = e.target.tagName.toLowerCase();
    if (tag === 'input' || tag === 'textarea') return;

    if (e.ctrlKey && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        undoCanvasState();
    } else if (e.ctrlKey && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        redoCanvasState();
    }
});

// ======= 自动交互记录 =======
function bindInteractionTracking() {
    const canvas = document.getElementById('iconCanvas');

    let recordTimeout;

    function delayedRecord() {
        clearTimeout(recordTimeout);
        recordTimeout = setTimeout(() => {
            recordCanvasState();
        }, 100); // 防抖处理
    }

    canvas.addEventListener('mouseup', delayedRecord);
    canvas.addEventListener('touchend', delayedRecord);
    canvas.addEventListener('click', delayedRecord);
    document.addEventListener('keydown', delayedRecord);
}

// ======= 初始化绑定 =======
bindInteractionTracking();

document.getElementById('undoBtn').addEventListener('click', () => {
    undoCanvasState(); // 上一步
    drawAll();         // 重新绘制画布
});

document.getElementById('redoBtn').addEventListener('click', () => {
    redoCanvasState(); // 下一步
    drawAll();         // 重新绘制画布
});
