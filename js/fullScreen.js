function enterFullScreen() {
    const container = document.getElementById("fullScreenContainer");
    const overlay = document.getElementById("timeOverlay");
    const canvas = document.getElementById("iconCanvas");

    const fsRequest =
        container.requestFullscreen ||
        container.webkitRequestFullscreen ||
        container.msRequestFullscreen;

    if (fsRequest) {
        fsRequest.call(container).then(() => {
            overlay.style.display = "block";
            scaleCanvasToFit(canvas); // ✅ 修正这里
            startClock();             // ✅ 开始时钟
        }).catch(err => {
            console.warn("Fullscreen failed:", err);
        });
    }

}

function scaleCanvasToFit(canvas) {
    const screenW = window.innerWidth;
    const screenH = window.innerHeight;
    const baseW = canvas.width;
    const baseH = canvas.height;

    // 根据屏幕宽高比例选择最小缩放值
    const scaleW = screenW / baseW;
    const scaleH = screenH / baseH;
    const scale = Math.min(scaleW, scaleH);

    // 应用缩放
    canvas.style.transform = `scale(${scale})`;
    canvas.style.transformOrigin = "top left"; // 🔄 重要：确保偏移计算准确
    canvas.style.position = "absolute";

    // 计算缩放后的宽高
    const scaledW = baseW * scale;
    const scaledH = baseH * scale;

    // 居中偏移（左上作为锚点）
    const offsetX = (screenW - scaledW) / 2;
    const offsetY = (screenH - scaledH) / 2;

    canvas.style.left = `${offsetX}px`;
    canvas.style.top = `${offsetY}px`;
    canvas.style.zIndex = "10";
}


function startClock() {
    updateClock();
    window.timeInterval = setInterval(updateClock, 1000);
}

function updateClock() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, "0");
    const m = String(now.getMinutes()).padStart(2, "0");
    const s = String(now.getSeconds()).padStart(2, "0");
    document.getElementById("timeOverlay").textContent = `${h}:${m}:${s}`;
}

document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement) {
        // 退出全屏时还原
        clearInterval(window.timeInterval);
        document.getElementById("timeOverlay").style.display = "none";
        const canvas = document.getElementById("iconCanvas");
        canvas.style = ""; // 清空样式
    }
});
