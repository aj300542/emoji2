let popupTimer = null;

function bindPopupToItems() {
    const items = document.querySelectorAll(".item");
    items.forEach(item => {
        if (!item.dataset.bound) {
            item.dataset.bound = "true";

            item.addEventListener("click", () => {
                const icon = item.querySelector(".char").textContent;
                const name = item.querySelector(".label").textContent;

                const popup = document.getElementById("popup");
                const popupIcon = document.getElementById("popup-icon");
                const popupName = document.getElementById("popup-name");

                popupIcon.textContent = icon;
                popupName.textContent = name;
                popup.style.transform = "translate(-50%, -50%) scale(1)";

                const contentToCopy = `${icon} ${name}`;
                navigator.clipboard.writeText(contentToCopy)
                    .then(() => console.log("✅ 已复制:", contentToCopy))
                    .catch(err => console.error("❌ 复制失败:", err));

                if (popupTimer) clearTimeout(popupTimer);
                popupTimer = setTimeout(() => {
                    popup.style.transform = "translate(-50%, -50%) scale(0)";
                    popupTimer = null;
                }, 1000);
            });
        }
    });
}

const galleryObserver = new MutationObserver(() => {
    bindPopupToItems();
});

document.addEventListener("DOMContentLoaded", () => {
    const gallery = document.getElementById("gallery");
    galleryObserver.observe(gallery, { childList: true });
});
