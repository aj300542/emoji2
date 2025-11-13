function renderCategory(type) {
    const gallery = document.getElementById("gallery");
    gallery.innerHTML = "";

    const path = `${JSON_BASE_PATH}${type}.json`; // ✅ 使用变量拼接路径

    fetch(path)
        .then(res => res.json())
        .then(list => {
            window.objectItems = list;

            list.forEach(item => {
                const div = document.createElement("div");
                div.className = "item";
                div.innerHTML = `
            <div class="char">${item.icon}</div>
            <div class="label">${item.name}</div>
          `;
                gallery.appendChild(div);
            });

            document.dispatchEvent(new Event("DOMContentLoaded"));
        })
        .catch(err => {
            gallery.innerHTML = `<p style="text-align:center;color:#c00;">❌ 无法加载分类：${type}</p>`;
            console.error(`❌ 加载 ${type} 分类失败:`, err);
        });
}

renderCategory(JSON_1); // ✅ 正确：传变量值