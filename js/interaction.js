
// interaction.js




// 鼠标按下
canvas.addEventListener("mousedown", (e) => {
    const mx = e.offsetX;
    const my = e.offsetY;

    if (e.ctrlKey || e.metaKey) {
        selectionBox = { startX: mx, startY: my, endX: mx, endY: my };
        return;
    }

    selectedIndex = null;
    selectedIndices = [];
    dragging = false;

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];
        const bounds = el.size;
        if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
            selectedIndex = i;
            selectedIndices = [i];
            dragIndex = i;
            offsetX = mx - el.x;
            offsetY = my - el.y;
            dragging = true;
            break;
        }
    }

    drawAll();
});

canvas.addEventListener("mousemove", (e) => {
    if (selectionBox) {
        selectionBox.endX = e.offsetX;
        selectionBox.endY = e.offsetY;
        drawAll(); // 在 drawAll 中添加框绘制
    }
});
canvas.addEventListener("mouseup", () => {
    if (selectionBox) {
        const x1 = Math.min(selectionBox.startX, selectionBox.endX);
        const x2 = Math.max(selectionBox.startX, selectionBox.endX);
        const y1 = Math.min(selectionBox.startY, selectionBox.endY);
        const y2 = Math.max(selectionBox.startY, selectionBox.endY);

        selectedIndices = [];

        elements.forEach((el, i) => {
            if (el.x > x1 && el.x < x2 && el.y > y1 && el.y < y2) {
                selectedIndices.push(i);
            }
        });

        selectionBox = null;
        drawAll();
        return;

    }

    dragging = false;
    dragIndex = null;
});
// 鼠标移动
canvas.addEventListener("mousemove", (e) => {
    if (!dragging || dragIndex === null) return;

    const mx = e.offsetX;
    const my = e.offsetY;
    const el = elements[dragIndex];

    if (el.type === "group") {
        // 群组使用累计偏移 dx/dy
        const dx = mx - offsetX;
        const dy = my - offsetY;
        el.x += dx;
        el.y += dy;
        offsetX = mx;
        offsetY = my;
    } else {
        // 普通元素使用鼠标位置减去初始偏移量
        el.x = mx - offsetX;
        el.y = my - offsetY;
    }

    drawAll();
});
canvas.addEventListener("mousedown", (e) => {
    const mx = e.offsetX;
    const my = e.offsetY;

    if (e.ctrlKey || e.metaKey) {
        selectionBox = { startX: mx, startY: my, endX: mx, endY: my };
        return;
    }

    selectedIndex = null;
    selectedIndices = [];
    dragging = false;
    dragIndex = null;

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];

        if (el.type === "group") {
            // 基于所有子元素计算群组的边界包围盒
            const bounds = el.children.reduce((acc, child) => {
                const cx = el.x + child.x;
                const cy = el.y + child.y;
                const hs = child.size / 2;
                return {
                    left: Math.min(acc.left, cx - hs),
                    right: Math.max(acc.right, cx + hs),
                    top: Math.min(acc.top, cy - hs),
                    bottom: Math.max(acc.bottom, cy + hs)
                };
            }, {
                left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity
            });

            if (mx >= bounds.left && mx <= bounds.right && my >= bounds.top && my <= bounds.bottom) {
                dragIndex = i;
                selectedIndex = i;
                selectedIndices = [i];
                offsetX = mx;
                offsetY = my;
                dragging = true;
                break;
            }
        } else {
            const bounds = el.size;
            if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
                dragIndex = i;
                selectedIndex = i;
                selectedIndices = [i];
                offsetX = mx - el.x;
                offsetY = my - el.y;
                dragging = true;
                break;
            }
        }
    }

    drawAll();
});
// 鼠标抬起
canvas.addEventListener("mouseup", () => {
    dragging = false;
    dragIndex = null;
});
// 滚轮缩放
canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const mx = e.offsetX;
    const my = e.offsetY;
    const delta = e.deltaY < 0 ? 0.1 : -0.1; // 控制缩放幅度

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];

        if (el.type === "group") {
            // ✅ 检测鼠标是否在群组包围盒范围内
            const bounds = el.children.reduce((acc, child) => {
                const cx = el.x + child.x;
                const cy = el.y + child.y;
                const hs = child.size / 2;
                return {
                    left: Math.min(acc.left, cx - hs),
                    right: Math.max(acc.right, cx + hs),
                    top: Math.min(acc.top, cy - hs),
                    bottom: Math.max(acc.bottom, cy + hs)
                };
            }, {
                left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity
            });

            if (mx >= bounds.left && mx <= bounds.right && my >= bounds.top && my <= bounds.bottom) {
                // ✅ 缩放整个群组：更新子元素尺寸、位置、父级缩放值
                el.scale = Math.max(0.2, el.scale + delta);

                el.children.forEach(child => {
                    child.size = Math.max(10, child.size * (1 + delta));
                    child.x *= (1 + delta);
                    child.y *= (1 + delta);
                });

                drawAll();
                break;
            }
        } else {
            // ✅ 普通元素缩放
            const bounds = el.size;
            if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
                el.size = Math.max(20, el.size + delta * 60); // 放大倍数更明显
                drawAll();
                break;
            }
        }
    }
}, { passive: false });

// 删除 & 取消选中 & 旋转
window.addEventListener("keydown", (e) => {
    // 删除选中元素
    if (e.key === "Delete" && selectedIndex !== null) {
        elements.splice(selectedIndex, 1);
        selectedIndex = null;
        drawAll();
        return;
    }

    // 取消选中
    if (e.key === "Escape") {
        selectedIndex = null;
        drawAll();
        return;
    }

    // 旋转选中元素（包含群组）
    if (selectedIndex !== null) {
        const el = elements[selectedIndex];
        const rotateStep = Math.PI / 18;
        if (e.key === "ArrowLeft") {
            el.rotation = (el.rotation || 0) - rotateStep;
            drawAll();
        }

        if (e.key === "ArrowRight") {
            el.rotation = (el.rotation || 0) + rotateStep;
            drawAll();
        }
        if (el.type === "group" && el.children) {
            const rotateStep = Math.PI / 18;
            el.rotation = (el.rotation || 0) + (e.key === "ArrowLeft" ? -rotateStep : rotateStep);

            // 🧠 计算群组真实中心点（基于子元素坐标）
            let sumX = 0, sumY = 0;
            el.children.forEach(child => {
                sumX += child.x;
                sumY += child.y;
            });
            const cx = sumX / el.children.length;
            const cy = sumY / el.children.length;

            // 🎯 绕群组中心旋转每个子元素
            el.children.forEach(child => {
                const dx = child.x - cx;
                const dy = child.y - cy;
                const angle = Math.atan2(dy, dx) + (e.key === "ArrowLeft" ? -rotateStep : rotateStep);
                const dist = Math.hypot(dx, dy);
                child.x = cx + dist * Math.cos(angle);
                child.y = cy + dist * Math.sin(angle);
                child.rotation = (child.rotation || 0) + (e.key === "ArrowLeft" ? -rotateStep : rotateStep);
            });
            drawAll();
        }
    }
});
// 双击置顶
canvas.addEventListener("dblclick", (e) => {
    const mx = e.offsetX;
    const my = e.offsetY;

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];

        if (el.type === "group") {
            // 计算群组的包围盒
            const bounds = el.children.reduce((acc, child) => {
                const cx = el.x + child.x;
                const cy = el.y + child.y;
                const hs = child.size / 2;
                return {
                    left: Math.min(acc.left, cx - hs),
                    right: Math.max(acc.right, cx + hs),
                    top: Math.min(acc.top, cy - hs),
                    bottom: Math.max(acc.bottom, cy + hs)
                };
            }, {
                left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity
            });

            // 检查鼠标是否在群组范围内
            if (mx >= bounds.left && mx <= bounds.right && my >= bounds.top && my <= bounds.bottom) {
                const [selected] = elements.splice(i, 1);
                elements.push(selected); // 置顶
                selectedIndex = elements.length - 1;
                drawAll();
                break;
            }

        } else {
            const bounds = el.size;
            if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
                const [selected] = elements.splice(i, 1);
                elements.push(selected); // 置顶
                selectedIndex = elements.length - 1;
                drawAll();
                break;
            }
        }
    }
});


let longPressTimer = null;
let longPressStartX = 0;
let longPressStartY = 0;
let lastTouchTap = 0;
let lastTouchDistance = null;
let lastTapX = 0;
let lastTapY = 0;



// 📱 触摸开始
canvas.addEventListener("touchstart", (e) => {
    const now = Date.now();
    const touch = e.touches[0];
    const rect = canvas.getBoundingClientRect();
    const mx = touch.clientX - rect.left;
    const my = touch.clientY - rect.top;

    const timeDelta = now - lastTouchTap;
    const distDelta = Math.hypot(mx - lastTapX, my - lastTapY);

    // ✅ 快速双击置顶元素（时间 < 300ms 且距离 < 20px）
    if (timeDelta < 300 && distDelta < 20) {
        for (let i = elements.length - 1; i >= 0; i--) {
            const el = elements[i];

            if (el.type === "group") {
                const bounds = el.children.reduce((acc, child) => {
                    const cx = el.x + child.x;
                    const cy = el.y + child.y;
                    const hs = child.size / 2;
                    return {
                        left: Math.min(acc.left, cx - hs),
                        right: Math.max(acc.right, cx + hs),
                        top: Math.min(acc.top, cy - hs),
                        bottom: Math.max(acc.bottom, cy + hs)
                    };
                }, {
                    left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity
                });

                if (mx >= bounds.left && mx <= bounds.right && my >= bounds.top && my <= bounds.bottom) {
                    const [selected] = elements.splice(i, 1);
                    elements.push(selected);
                    selectedIndex = elements.length - 1;
                    drawAll();
                    break;
                }
            } else {
                const bounds = el.size;
                if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
                    const [selected] = elements.splice(i, 1);
                    elements.push(selected);
                    selectedIndex = elements.length - 1;
                    drawAll();
                    break;
                }
            }
        }

        lastTouchTap = 0;
        lastTapX = 0;
        lastTapY = 0;
        return;
    }

    // ✅ 记录本次触点
    lastTouchTap = now;
    lastTapX = mx;
    lastTapY = my;

    longPressStartX = mx;
    longPressStartY = my;

    // ✅ 长按静止取消选中
    longPressTimer = setTimeout(() => {
        if (selectedIndex !== null) {
            selectedIndex = null;
            selectedIndices = [];
            drawAll();
        }
    }, 600);

    // ✅ 双指轻点取消选中（备用方式）
    if (e.touches.length === 2 && now - lastTouchTap < 400) {
        selectedIndex = null;
        selectedIndices = [];
        drawAll();
    }

    // ✅ 拖动选中逻辑
    selectedIndex = null;
    selectedIndices = [];
    dragging = false;
    dragIndex = null;

    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];
        const bounds = el.size;

        if (el.type === "group") {
            const bounds = el.children.reduce((acc, child) => {
                const cx = el.x + child.x;
                const cy = el.y + child.y;
                const hs = child.size / 2;
                return {
                    left: Math.min(acc.left, cx - hs),
                    right: Math.max(acc.right, cx + hs),
                    top: Math.min(acc.top, cy - hs),
                    bottom: Math.max(acc.bottom, cy + hs)
                };
            }, {
                left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity
            });

            if (mx >= bounds.left && mx <= bounds.right && my >= bounds.top && my <= bounds.bottom) {
                dragIndex = i;
                selectedIndex = i;
                selectedIndices = [i];
                offsetX = mx;
                offsetY = my;
                dragging = true;
                break;
            }
        } else {
            if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
                dragIndex = i;
                selectedIndex = i;
                selectedIndices = [i];
                offsetX = mx - el.x;
                offsetY = my - el.y;
                dragging = true;
                break;
            }
        }
    }

    drawAll();
    e.preventDefault();
}, { passive: false });




// 📱 触摸移动（双指缩放 + 单指拖动）
canvas.addEventListener("touchmove", (e) => {
    const rect = canvas.getBoundingClientRect();

    // ✅ 判断是否移动，取消长按
    const touch = e.touches[0];
    const mx = touch.clientX - rect.left;
    const my = touch.clientY - rect.top;
    const dx = Math.abs(mx - longPressStartX);
    const dy = Math.abs(my - longPressStartY);
    const moveThreshold = 10;
    if (dx > moveThreshold || dy > moveThreshold) {
        clearTimeout(longPressTimer);
    }

    // ✅ 双指缩放
    if (e.touches.length === 2) {
        const t1 = e.touches[0];
        const t2 = e.touches[1];
        const x1 = t1.clientX - rect.left;
        const y1 = t1.clientY - rect.top;
        const x2 = t2.clientX - rect.left;
        const y2 = t2.clientY - rect.top;

        const currentDistance = Math.hypot(x2 - x1, y2 - y1);

        if (lastTouchDistance !== null) {
            const delta = currentDistance - lastTouchDistance;
            const scaleDelta = delta / 100;
            const mx = (x1 + x2) / 2;
            const my = (y1 + y2) / 2;

            for (let i = elements.length - 1; i >= 0; i--) {
                const el = elements[i];
                if (el.type === "group") {
                    const bounds = el.children.reduce((acc, child) => {
                        const cx = el.x + child.x;
                        const cy = el.y + child.y;
                        const hs = child.size / 2;
                        return {
                            left: Math.min(acc.left, cx - hs),
                            right: Math.max(acc.right, cx + hs),
                            top: Math.min(acc.top, cy - hs),
                            bottom: Math.max(acc.bottom, cy + hs)
                        };
                    }, {
                        left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity
                    });

                    if (mx >= bounds.left && mx <= bounds.right && my >= bounds.top && my <= bounds.bottom) {
                        el.scale = Math.max(0.2, el.scale + scaleDelta);
                        el.children.forEach(child => {
                            child.size = Math.max(10, child.size * (1 + scaleDelta));
                            child.x *= (1 + scaleDelta);
                            child.y *= (1 + scaleDelta);
                        });
                        drawAll();
                        break;
                    }
                } else {
                    const bounds = el.size;
                    if (Math.abs(mx - el.x) < bounds / 2 && Math.abs(my - el.y) < bounds / 2) {
                        el.size = Math.max(20, el.size + scaleDelta * 60);
                        drawAll();
                        break;
                    }
                }
            }
        }

        lastTouchDistance = currentDistance;
        e.preventDefault();
        return;
    }

    // ✅ 单指拖动
    if (e.touches.length === 1) {
        if (!dragging || dragIndex === null) return;

        const el = elements[dragIndex];
        if (el.type === "group") {
            const dx = mx - offsetX;
            const dy = my - offsetY;
            el.x += dx;
            el.y += dy;
            offsetX = mx;
            offsetY = my;
        } else {
            el.x = mx - offsetX;
            el.y = my - offsetY;
        }

        drawAll();
        e.preventDefault();
    }
}, { passive: false });



// 📱 触摸结束
canvas.addEventListener("touchend", (e) => {
    clearTimeout(longPressTimer);
    longPressTimer = null;
    lastTouchDistance = null;
    dragging = false;
    dragIndex = null;

    // ✅ 框选处理
    if (selectionBox) {
        const x1 = Math.min(selectionBox.startX, selectionBox.endX);
        const x2 = Math.max(selectionBox.startX, selectionBox.endX);
        const y1 = Math.min(selectionBox.startY, selectionBox.endY);
        const y2 = Math.max(selectionBox.startY, selectionBox.endY);

        selectedIndices = [];

        elements.forEach((el, i) => {
            if (el.x > x1 && el.x < x2 && el.y > y1 && el.y < y2) {
                selectedIndices.push(i);
            }
        });

        selectionBox = null;
        drawAll();
    }
});




