document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("gallery");
  let popupTimer = null; // ⏱️ 用于记录当前的定时器

  container.querySelectorAll(".item").forEach((el, index) => {
    el.setAttribute("data-index", index);
    el.addEventListener("click", () => {
      const clickedItem = objectItems[index];

      const popup = document.getElementById("popup");
      const popupIcon = document.getElementById("popup-icon");
      const popupName = document.getElementById("popup-name");

      popupIcon.textContent = clickedItem.icon;
      popupName.textContent = clickedItem.name;
      popup.style.transform = "translate(-50%, -50%) scale(1)";

      const contentToCopy = `${clickedItem.icon} ${clickedItem.name}`;
      navigator.clipboard.writeText(contentToCopy)
        .then(() => console.log("已复制到剪贴板:", contentToCopy))
        .catch(err => console.error("复制失败:", err));

      // 🔄 如果已有定时器，则清除它
      if (popupTimer) clearTimeout(popupTimer);

      // ⏲️ 启动新的定时器
      popupTimer = setTimeout(() => {
        popup.style.transform = "translate(-50%, -50%) scale(0)";
        popupTimer = null;
      }, 1000);
    });
  });
});
// 监听 gallery 中所有 .item 的 emoji 双击事件
document.addEventListener('DOMContentLoaded', () => {
  const gallery = document.getElementById('gallery');

  // 使用事件委托监听 .char 的双击
  gallery.addEventListener('dblclick', (event) => {
    const target = event.target;
    if (target.classList.contains('char')) {
      const emoji = target.textContent.trim();
      const encoded = encodeURIComponent(emoji);
      // 跳转到根目录下的 download.html
      const isGitHubPages = window.location.hostname === 'aj300542.github.io';
      // 线上用绝对路径，本地用相对路径（../ 跳出 bios 目录）
      const path = isGitHubPages ? '/emoji2/downloadobj.html' : '../downloadobj.html';
      window.location.href = `${path}?emoji=${encoded}`;
    }
  });
});
// 先判断环境，和你3D文件的逻辑保持一致
const isGitHubPages = window.location.hostname === 'aj300542.github.io';

// 字体路径：本地直接指向font目录，线上加/emoji前缀
const fontPath = isGitHubPages ? '/emoji2/font/NotoColorEmoji-Regular.ttf' : './font/NotoColorEmoji-Regular.ttf';

// 动态创建@font-face样式并插入页面
const fontStyle = document.createElement('style');
fontStyle.textContent = `
@font-face {
    font-family: 'SegoeEmojiOld';
    src: url('${fontPath}') format('truetype');
    font-display: swap;
}
body {
    font-family: 'SegoeEmojiOld', 'Segoe UI', sans-serif;
}
.char {
    font-family: 'SegoeEmojiOld', 'Segoe UI Emoji', sans-serif;
}
`;
