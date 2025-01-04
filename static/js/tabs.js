function openTab(evt, tabName) {
    const tabcontent = document.getElementsByClassName('tabcontent');
    const tablinks = document.getElementsByClassName('tablinks');

    for (let i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = 'none';
    }

    for (let i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(' active', '');
    }

    document.getElementById(tabName).style.display = 'block';
    evt.currentTarget.className += ' active';
}

