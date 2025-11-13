document.addEventListener("DOMContentLoaded", () => {
    const gallery = document.getElementById("gallery");
    const popup = document.getElementById("popup");
    const popupIcon = document.getElementById("popup-icon");
    const popupName = document.getElementById("popup-name");

    let timeoutHandle = null;

    gallery.addEventListener("click", (e) => {
        const card = e.target.closest(".item");
        if (!card) return;

        const icon = card.querySelector(".char").textContent;
        const name = card.querySelector(".label").textContent;

        popupIcon.textContent = icon;
        popupName.textContent = name;

        popup.style.transform = "translate(-50%, -50%) scale(1)";
        popup.style.pointerEvents = "auto";

        // 👇 复制到剪贴板
        const combinedText = `${icon} ${name}`;
        navigator.clipboard.writeText(combinedText).then(() => {
            console.log("已复制到剪贴板:", combinedText);
        }).catch(err => {
            console.error("复制失败:", err);
        });

        // 👇 重置消失计时器
        clearTimeout(timeoutHandle);
        timeoutHandle = setTimeout(() => {
            popup.style.transform = "translate(-50%, -50%) scale(0)";
            popup.style.pointerEvents = "none";
        }, 1000);
    });
});
