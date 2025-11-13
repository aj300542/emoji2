const gallery = document.getElementById("gallery");

fetch(jsonpath) // ✅ 使用变量，不加引号
    .then(response => response.json())
    .then(objectItems => {
        window.objectItems = objectItems;

        objectItems.forEach(item => {
            const div = document.createElement("div");
            div.className = "item";
            div.innerHTML = `
          <div class="char">${item.icon}</div>
          <p>${item.name}</p>
        `;
            gallery.appendChild(div);
        });

        document.dispatchEvent(new Event("DOMContentLoaded"));
    })
    .catch(error => {
        console.error("❌ 加载 JSON 文件失败：", error);
    });