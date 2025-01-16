function openEditModal(username, email, role, wins, losses, tickets) {
    document.getElementById('edit-username').value = username;
    document.getElementById('edit-email').value = email;
    document.getElementById('edit-role').value = role;
    document.getElementById('edit-wins').value = wins;
    document.getElementById('edit-losses').value = losses;
    document.getElementById('edit-tickets').value = tickets;

    openModal('edit-user-modal');
}

document.addEventListener('DOMContentLoaded', () => {
    // Replace or complement the server-side data
    fetchAndRenderUsers();
    fetchAndRenderReports();
    fetchAndRenderSleeves();
});

function fetchAndRenderUsers() {
    console.log('clicked');
    const username = document.getElementById('username-search').value;

    const url = new URL('/admin/get_users', window.location.origin);
    if (username) url.searchParams.append('username', username);

    fetch(url)
        .then(res => res.json())
        .then(data => {
            const usersTableBody = document.getElementById('user-table-body');
            if (!usersTableBody) return;
            usersTableBody.innerHTML = '';

            // Note "user" instead of "users" and an innerHTML
            data.users.forEach(user => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${user.username}</td>
                    <td>${user.email}</td>
                    <td>${user.role}</td>
                    <td>${user.wins}</td>
                    <td>${user.losses}</td>
                    <td>${user.tickets}</td>
                    <td class="user"> 
                        <button class="btn-primary user" onclick="openEditModal('${user.username}', '${user.email}', '${user.role}', ${user.wins}, ${user.losses}, ${user.tickets})">Edit</button>
                        <button class="btn-danger user" onclick="confirmDeleteUser('${user.username}')">Delete</button>
                    </td>
                `;
                usersTableBody.appendChild(tr);
            });
        })
        .catch(err => console.error('Error fetching users:', err));
}

function fetchAndRenderReports() {
    const reportingUser = document.getElementById('user-reporting').value;
    const reportedUser = document.getElementById('reported-user').value;
    const reportType = document.getElementById('report-type').value;

    const url = new URL('/admin/get_reports', window.location.origin);
    if (reportingUser) url.searchParams.append('user-reporting', reportingUser);
    if (reportedUser) url.searchParams.append('reported-user', reportedUser);
    if (reportType) url.searchParams.append('report-type', reportType);

    fetch(url)
        .then(res => res.json())
        .then(data => {
            const reportsTableBody = document.getElementById('reports-table-body');
            if (!reportsTableBody) return;
            reportsTableBody.innerHTML = '';

            data.reports.forEach(report => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${report.id}</td>
                    <td>${report.user_reporting}</td>
                    <td>${report.user_being_reported}</td>
                    <td>${report.report_type}</td>
                    <td>${report.detail}</td>
                    <td>
                        <button class="btn-danger" onclick="confirmDeleteReport('${report.id}')">Delete</button>
                    </td>
                `;
                reportsTableBody.appendChild(tr);
            });
            if (data.reports.length === 0) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td colspan="6">No Reports found</td>`;
                reportsTableBody.appendChild(tr);
            }
        })
        .catch(err => console.error('Error fetching reports:', err));
}

document.getElementById('report-filter-panel').addEventListener('submit', function(event) {
    event.preventDefault();
    fetchAndRenderReports();
});

function fetchAndRenderSleeves() {
    const searchSleeve = document.getElementById('search').value;
    const url = new URL('/admin/get_sleeves', window.location.origin);
    if (searchSleeve) {
        url.searchParams.append('search_sleeve', searchSleeve);
    }

    fetch(url, { method: 'GET' }
    )
        .then(response => response.json())
        .then(data => {
            const sleevesContainer = document.getElementById('sleeves-container');
            if (!sleevesContainer) return;

            const sleevesByType = {};
            data.sleeves.forEach(sleeve => {
                if (!sleevesByType[sleeve.sleeve_type]) {
                    sleevesByType[sleeve.sleeve_type] = [];
                }
                sleevesByType[sleeve.sleeve_type].push(sleeve);
            });
            sleevesContainer.innerHTML = '';

            for (const [type, sleeves] of Object.entries(sleevesByType)) {
                const section = document.createElement('div');
                section.className = 'sleeve-section';

                const heading = document.createElement('h2');
                heading.textContent = `Type: ${type}`;
                section.appendChild(heading);

                const sleeveGrid = document.createElement('div');
                sleeveGrid.className = 'sleeve-grid';

                sleeves.forEach(sleeve => {
                    const item = document.createElement('div');
                    item.className = 'sleeve-item';
                    item.innerHTML = `
                        <img src="${sleeve.sleeve}" alt="Sleeve ${sleeve.id}">
                        <p>Sleeve ID: ${sleeve.id}</p>
                        <button class="btn-danger" onclick="confirmDeleteSleeve('${sleeve.id}')">Delete</button>
                    `;
                    sleeveGrid.appendChild(item);
                });

                section.appendChild(sleeveGrid);
                sleevesContainer.appendChild(section);
            }
        })
        .catch(err => {
            console.error('Error fetching sleeves:', err);
            showModal('Failed to fetch sleeves', 'error');
        });
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
                fetchAndRenderUsers();
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
            fetchAndRenderReports();
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
            fetchAndRenderUsers();
        } else {
            showModal(data.message, 'error');
        }
    })
    .catch(() => showModal('An unexpected error occurred. Please try again later.', 'error'))
    .finally(() => closeModal('edit-user-modal'));
});

const displayModal = document.getElementById('modal');
function closeDisplayModal() {
    displayModal.style.display = 'none'; 
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
            fetchAndRenderSleeves();
            closeAddSleeveModal();
        } else if (data.error) {
            showModal(data.error, "error");
        } else {
            showModal("An unknown error occurred.", "error");
        }
    })
    .catch(error => {
        console.error("Error adding sleeve:", error);
        showModal("Error adding sleeve", "error");
    });
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
        if (data.message && !data.error) {
            showModal(data.message, 'success');
            fetchAndRenderSleeves();
        } else {
            const msg = data.message || data.error || "An error occurred deleting sleeve.";
            showModal(msg, 'error');
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