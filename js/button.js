document.addEventListener('DOMContentLoaded', () => {
    // 1. 第一步：动态获取基础路径（必须先定义）
    const basePath = window.location.pathname.includes('/emoji/') ? '/emoji' : '';

    // 2. 第二步：处理所有以 / 开头的站内 <a> 标签（放在这里！）
    const allSiteLinks = document.querySelectorAll('a[href^="/"]');
    allSiteLinks.forEach(link => {
        const originalHref = link.getAttribute('href');
        link.setAttribute('href', `${basePath}${originalHref}`);
    });

    // 3. 第三步：原有按钮绑定逻辑（放在后面，顺序不影响）
    const backHomeBtn = document.getElementById('backHome');
    if (backHomeBtn) {
        backHomeBtn.addEventListener('click', () => {
            window.location.href = `${basePath}/index.html`;
        });
    }

    const biosBtn = document.getElementById('bios');
    if (biosBtn) {
        biosBtn.addEventListener('click', () => {
            window.location.href = `${basePath}/bios.html`;
        });
    }

    const objectBtn = document.getElementById('object');
    if (objectBtn) {
        objectBtn.addEventListener('click', () => {
            window.location.href = `${basePath}/objects.html`;
        });
    }

    const knowledgeBtn = document.getElementById('knowledge');
    if (knowledgeBtn) {
        knowledgeBtn.addEventListener('click', () => {
            window.location.href = `${basePath}/knowledge.html`;
        });
    }

    const opennewBtn = document.getElementById('opennew');
    if (opennewBtn) {
        opennewBtn.addEventListener('click', () => {
            window.open("https://aj300542.github.io/download.html", "_blank");
        });
    }
});