let wakeLock = null;

// 检查浏览器是否支持 Wake Lock API
const canWakeLock = () => 'wakeLock' in navigator;

// 请求唤醒锁
const requestWakeLock = async () => {
    try {
        if (canWakeLock()) {
            wakeLock = await navigator.wakeLock.request('screen');
            console.log('Wake Lock is active!');
        }
    } catch (err) {
        console.log(`${err.name}, ${err.message}`);
    }
};

// 释放唤醒锁
const releaseWakeLock = () => {
    if (wakeLock !== null) {
        wakeLock.release().then(() => {
            wakeLock = null;
        });
    }
};

// 监听唤醒锁释放
if (wakeLock !== null) {
    wakeLock.addEventListener('release', () => {
        console.log('Wake Lock has been released');
    });
}

// 重新获取唤醒锁
document.addEventListener('visibilitychange', async () => {
    if (wakeLock !== null && document.visibilityState === 'visible') {
        requestWakeLock();
    }
});

// 开始请求唤醒锁
requestWakeLock();
