function openEditModal(username, email, role, wins, losses, tickets) {
    document.getElementById('edit-username').value = username;
    document.getElementById('edit-email').value = email;
    document.getElementById('edit-role').value = role;
    document.getElementById('edit-wins').value = wins;
    document.getElementById('edit-losses').value = losses;
    document.getElementById('edit-tickets').value = tickets;

    openModal('edit-user-modal');
}

function confirmDeleteUser(username) {
    const deleteModal = document.getElementById('confirm-delete-modal');
    deleteModal.dataset.username = username; 
    openModal('confirm-delete-modal');
}

function confirmDeleteReport(id) {
    const deleteModal = document.getElementById('confirm-delete-report-modal');
    deleteModal.dataset.id = id; 
    openModal('confirm-delete-report-modal');
}

function confirmDeleteSleeve(sleeveId) {
    const deleteModal = document.getElementById('confirm-delete-sleeve-modal');
    deleteModal.dataset.id = sleeveId; 
    openModal('confirm-delete-sleeve-modal');
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'block';
}

function closeModal(modalId = null) {
    if (modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.style.display = 'none';
    } else {
        const modals = document.querySelectorAll('.esoteric-modal');
        modals.forEach(modal => (modal.style.display = 'none'));
    }
}

function deleteUser() {
    const username = document.getElementById('confirm-delete-modal').dataset.username;

    fetch(`/admin/delete_account/${username}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showModal(data.message, 'success');

            } else {
                showModal(data.message, 'error');
            }
        })
        .catch(() => showModal('An unexpected error occurred. Please try again later.', 'error'))
        .finally(() => closeModal('confirm-delete-modal'));
}

function deleteReport() {
    const id = document.getElementById('confirm-delete-report-modal').dataset.id;

    fetch(`/admin/delete_report/${id}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showModal(data.message, 'success');
            } else {
                showModal(data.message, 'error');
            }
        })
        .catch(() => showModal('An unexpected error occurred. Please try again later.', 'error'))
        .finally(() => closeModal('confirm-delete-report-modal'));
}

const editUserForm = document.getElementById('editUserForm');
editUserForm.addEventListener('submit', function (event) {
    event.preventDefault(); 

    const formData = new FormData(editUserForm);

    fetch('/admin/update_user', {
        method: 'POST',
        body: formData,
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showModal(data.message, 'success');
            } else {
                showModal(data.message, 'error');
            }
        })
        .catch(() => showModal('An unexpected error occurred. Please try again later.', 'error'))
        .finally(() => closeModal());
});

const displayModal = document.getElementById('modal');
function closeDisplayModal() {
    displayModal.style.display = 'none'; 
    window.location.reload();
}

displayModal.addEventListener('click', function(event) {
    if (event.target === displayModal) {
        closeDisplayModal();
    }
});

function toggleFilter() {
    var filterPanel = document.getElementById('report-filter-panel');
    if (filterPanel.style.display === 'none' || filterPanel.style.display === '') {
        filterPanel.style.display = 'block';
    } else {
        filterPanel.style.display = 'none';
    }
}

function resetFilter() {
    document.getElementById('user-reporting').value = '';
    document.getElementById('reported-user').value = '';
    document.getElementById('report-type').value = '';
}

// Sleeves
function openAddSleeveModal() {
    document.getElementById("add-sleeve-modal").style.display = "block";
}

function closeAddSleeveModal() {
    document.getElementById("add-sleeve-modal").style.display = "none";
}

function submitAddSleeveForm() {
    const form = document.getElementById("add-sleeve-form");
    const formData = new FormData(form);

    fetch("/admin/sleeves", {
        method: "POST",
        body: formData,
    })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                showModal(data.message, "success");
                location.reload();
            }
        })
        .catch(error => console.error("Error adding sleeve:", error));
}

function deleteSleeve() {
    const sleeveId = document.getElementById('confirm-delete-sleeve-modal').dataset.id;

    fetch(`/admin/sleeves/delete/${sleeveId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showModal(data.message, 'success');
            } else {
                showModal(data.message, 'error');
            }
        })
        .catch(() => showModal('An unexpected error occurred. Please try again later.', 'error'))
        .finally(() => closeModal('confirm-delete-sleeve-modal'));
}


function updateFileName() {
    const input = document.getElementById('sleeve-image');
    const fileName = input.files.length > 0 ? input.files[0].name : 'No file chosen';
    document.getElementById('file-name').textContent = fileName;
}
