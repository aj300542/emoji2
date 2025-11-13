
let sceneLoaded = false;

let currentScene = [];

function setScene(newElements) {
    if (!Array.isArray(newElements) || newElements.length === 0) {
        console.warn("⛔ setScene 被调用但数据无效");
        sceneLoaded = false;
        currentScene = [];
        return;
    }

    elements = newElements.map(obj => ({
        ...obj,
        rotationSwing: 0,
        animationHandle: null
    }));

    currentScene = elements;
    sceneLoaded = true;
    drawAll();
    console.log("✅ 新场景已设置，元素数：", currentScene.length);
    // 🌀 自动恢复动画状态
    if (typeof restoreAnimations === "function") {
        restoreAnimations(elements);
    }
}

function loadSceneFromFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
        try {
            const data = JSON.parse(reader.result);
            const loadedElements = Array.isArray(data)
                ? data
                : Array.isArray(data.elements)
                    ? data.elements
                    : [];

            if (loadedElements.length === 0) {
                alert("⚠️ 文件内容为空");
                return;
            }

            setScene(loadedElements);      // ✅ 初始化场景
            saveInitialStates();           // ✅ 记录初始状态（位置、旋转、尺寸等）

        } catch (err) {
            console.error("❌ 文件解析失败:", err);
            alert("载入失败：请确认 JSON 格式正确");
            sceneLoaded = false;
            currentScene = [];
        }
    };

    reader.readAsText(file);
}


async function saveSceneAsFile() {
    console.log("🧪 保存前调试：sceneLoaded =", sceneLoaded);
    console.log("🧪 保存前调试：currentScene.length =", currentScene.length);

    if (!sceneLoaded || !currentScene.length) {
        alert("❗场景尚未载入或为空，无法保存！");
        console.warn("⚠️ 保存中止：sceneLoaded =", sceneLoaded, "，currentScene.length =", currentScene.length);
        return;
    }

    const data = JSON.stringify(currentScene, null, 2);
    const blob = new Blob([data], { type: 'application/json' });

    try {
        const fileHandle = await window.showSaveFilePicker({
            suggestedName: "scene.json",
            types: [{
                description: "JSON 文件",
                accept: { "application/json": [".json"] }
            }]
        });

        const writable = await fileHandle.createWritable();
        await writable.write(blob);
        await writable.close();
        console.log("✅ 场景已成功保存！");
    } catch (err) {
        console.error("❌ 保存失败：", err);
    }
}

async function saveCanvasAsImageWithPicker() {
    const canvas = document.getElementById("iconCanvas");
    const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));

    try {
        const handle = await window.showSaveFilePicker({
            suggestedName: "scene.png",
            types: [{
                description: "PNG Image",
                accept: { "image/png": [".png"] }
            }]
        });

        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        alert("保存成功 🎉");
    } catch (err) {
        console.error("保存失败", err);
        alert("保存已取消或失败 ❌");
    }
}