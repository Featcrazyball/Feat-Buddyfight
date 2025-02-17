window.addEventListener('load', function () {
    const topBar = document.querySelector(".top-bar");
    topBar.classList.add("show");
});

let topBar = document.querySelector('.top-bar');
let lastScrollY = window.scrollY;

window.addEventListener('scroll', () => {
    if (window.scrollY < lastScrollY) {
        topBar.classList.add("show");
    } else if (window.scrollY > lastScrollY) {
        topBar.classList.remove("show");
    }
    lastScrollY = window.scrollY; 
});

function toggleMenu() {
    const navList = document.getElementById('listOfEverything');
    navList.classList.toggle('active');
}