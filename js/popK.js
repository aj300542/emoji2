let popupTimer = null;

function bindPopupToItems() {
  const items = document.querySelectorAll(".item");

  items.forEach(item => {
    // 防止重复绑定
    if (!item.dataset.bound) {
      item.dataset.bound = "true";

      item.addEventListener("click", () => {
        const icon = item.querySelector(".char").textContent;
        const name = item.querySelector("p").textContent;

        const popup = document.getElementById("popup");
        const popupIcon = document.getElementById("popup-icon");
        const popupName = document.getElementById("popup-name");

        popupIcon.textContent = icon;
        popupName.textContent = name;
        popup.style.transform = "translate(-50%, -50%) scale(1)";
        popup.style.pointerEvents = "auto";

        // 👇 自动复制到剪贴板
        const combinedText = `${icon} ${name}`;
        navigator.clipboard.writeText(combinedText)
          .then(() => console.log("已复制到剪贴板:", combinedText))
          .catch(err => console.error("复制失败:", err));

        // 👇 重置定时器，确保再次点击重新计时
        clearTimeout(popupTimer);
        popupTimer = setTimeout(() => {
          popup.style.transform = "translate(-50%, -50%) scale(0)";
          popup.style.pointerEvents = "none";
        }, 1000);
      });
    }
  });
}

// 自动监听 gallery 的变化（仅当你动态切换内容时需要）
const galleryObserver = new MutationObserver(() => {
  bindPopupToItems();
});

document.addEventListener("DOMContentLoaded", () => {
  const gallery = document.getElementById("gallery");
  galleryObserver.observe(gallery, { childList: true, subtree: false });

  // 🌟 首次渲染后绑定点击事件
  bindPopupToItems();
});
