const navLinks = {
    home: {
        href: "/",
        target: "_self",
        icon: null
    },
    discord: {
        href: "/server",
        target: "_blank",
        icon: "/assets/discord.svg"
    },
    github: {
        href: "//github.com/dragdev-studios",
        target: "_blank",
        icon: "/assets/github.svg"
    },
    bots: {
        href: "/about/bots/index.html",
        target: "_self",
        icon: null
    }
}

function createNav() {
    const elements = document.getElementsByTagName("nav");
    if(elements.length === 0) {
        console.warn("No navbar to insert into!");
        return;
    };
    const nav = elements[0];

    for(let key of Object.keys(navLinks)) {
        let container = document.createElement("div");
        let img = document.createElement("img");
        img.classList.add("icon");
        let linkContainer = document.createElement("a");
        
        let entry = navLinks[key];
        if(entry.icon!==null) {
            img.src = entry.icon;
            img.alt = "&zwsp;";
        };
        linkContainer.href = entry.href;
        linkContainer.target = entry.target;
        linkContainer.textContent = key;

        container.appendChild(img);
        container.appendChild(linkContainer);
        nav.appendChild(container);
    }l
};
