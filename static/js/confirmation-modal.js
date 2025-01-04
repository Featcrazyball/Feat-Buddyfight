function showConfirmationModal() {
    const modal = document.getElementById('confirmation-modal');
    modal.classList.add('visible');
}

function hideConfirmationModal() {
    const modal = document.getElementById('confirmation-modal');
    modal.classList.remove('visible');
}

document.getElementById('confirmation-modal').addEventListener('click', function (event) {
    const modalContent = document.querySelector('.confirm-modal-content');
    if (!modalContent.contains(event.target)) {
        hideConfirmationModal();
    }
});

document.querySelector('.confirm-modal-content').addEventListener('click', function (event) {
    event.stopPropagation();
});

document.getElementById('confirm-no').addEventListener('click', function () {
    hideConfirmationModal();
});

// please add an event listener for in the html page if u intend on using this