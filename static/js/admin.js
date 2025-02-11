function openEditModal(username, email, role, wins, losses, tickets) {
    document.getElementById('edit-username').value = username;
    document.getElementById('edit-email').value = email;
    document.getElementById('edit-role').value = role;
    document.getElementById('edit-wins').value = wins;
    document.getElementById('edit-losses').value = losses;
    document.getElementById('edit-tickets').value = tickets;

    openModal('edit-user-modal');
}

function openUpdateAnimeModal(id, ep_number, anime_season, urlVideo) {
    document.getElementById('update-episode').value = ep_number;
    document.getElementById('update-season').value = anime_season;
    document.getElementById('update-url').value = urlVideo;

    const updateModal = document.getElementById('edit-anime-modal');
    updateModal.dataset.id = id; 

    openModal('edit-anime-modal');
}

document.addEventListener('DOMContentLoaded', () => {
    // Replace or complement the server-side data
    fetchAndRenderUsers();
    fetchAndRenderReports();
    fetchAndRenderSleeves();
    fetchAndRenderPayments();
    drawMatchGraph();
    drawPaymentsGraph();
    fetchAndRenderAnime()
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
                const reportTable = document.getElementById('reports-table');
                reportsTableBody.innerHTML = '';
                if (reportTable) {
                    const tr = document.createElement('h1');
                    tr.style.height = '100%';
                    tr.style.textAlign = 'center';
                    tr.style.width = '100%';
                    tr.textContent = 'No reports found';
                    reportsTableBody.appendChild(tr);
                }
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

function togglePaymentFilter() {
    const filterPanel = document.getElementById('payment-filter-panel');
    if (filterPanel.style.display === 'none' || filterPanel.style.display === '') {
        filterPanel.style.display = 'block';
    } else {
        filterPanel.style.display = 'none';
    }
}

function resetPaymentFilter() {
    document.getElementById('user-payment').value = '';
    document.getElementById('payment-amount').value = '';
    document.getElementById('item-count').value = '';
}

function fetchAndRenderPayments() {
    const userPaying = document.getElementById('user-payment').value;
    const paymentAmount = document.getElementById('payment-amount').value;
    const itemCount = document.getElementById('item-count').value;

    const url = new URL('/admin/get_payment', window.location.origin);
    if (userPaying) url.searchParams.append('user-payment', userPaying);
    if (paymentAmount) url.searchParams.append('payment-amount', paymentAmount);
    if (itemCount) url.searchParams.append('item-count', itemCount);

    fetch(url)
        .then(response => response.json())
        .then(data => {
            const paymentsTableBody = document.getElementById('payments-table-body');
            if (!paymentsTableBody) return;
            paymentsTableBody.innerHTML = '';

            let totalAmount = 0;
            let NoTickets = 0;
            let distinctUsers = 0;
            let dateRanger;

            if (data.payments.length != 0) {
                data.payments.forEach(payment => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${payment.id}</td>
                        <td>${payment.username}</td>
                        <td>${payment.item_id}</td>
                        <td>$${payment.item_price.toFixed(2)}</td>
                        <td>${payment.date}</td>
                    `;
                    paymentsTableBody.appendChild(tr);
                    totalAmount += payment.item_price;
                    NoTickets += payment.item_id;
                    // Count distinct users
                    if (payment.username !== data.payments[data.payments.length - 1].username) {
                        distinctUsers++;
                    }
                    // Get date range 
                    if (!dateRanger) {
                        dateRanger = payment.date;
                    } else {
                        dateRanger = `${data.payments[0].date} - ${data.payments[data.payments.length - 1].date}`;
                    }
                    
                });
                const end = document.createElement('tr');
                end.innerHTML = `
                    <td>${data.payments.length} Payments Total</td>
                    <td>${distinctUsers} Users</td>
                    <td>${NoTickets}</td>
                    <td>$${totalAmount.toFixed(2)}</td>
                    <td>${dateRanger}</td>
                `;
                paymentsTableBody.appendChild(end);
            } else

            if (data.payments.length === 0) {
                const paymentsTable = document.getElementById('payments-table');
                paymentsTableBody.innerHTML = '';
                if (paymentsTable) {
                    const tr = document.createElement('h1');
                    tr.style.height = '100%';
                    tr.style.textAlign = 'center';
                    tr.style.width = '100%';
                    tr.textContent = 'No Payments Found';
                    paymentsTableBody.appendChild(tr);
                }
            }
        })
        .catch(err => console.error('Error fetching payments:', err));
}

function drawPaymentsGraph() {
    fetch('/admin/payment_history')
    .then(response => response.json())
    .then(data => {
        if (typeof Highcharts !== 'undefined') {
            Highcharts.chart('cash-sheet', {
                chart: {
                    type: 'line'
                },
                title: { text: 'No. of Tickets Bought' },
                xAxis: { type: 'datetime' },
                series: [{
                    name: 'Tickets Bought',
                    data: data.payment_data
                }]
            });
        } else {
            console.error('Highcharts library is not loaded.');
        }
    })
    .catch(err => console.error('Error fetching payment history:', err));
}

function drawMatchGraph() {
    fetch('/admin/match_history')
    .then(response => response.json())
    .then(data => {
        if (typeof Highcharts !== 'undefined') {
            Highcharts.chart('matches-sheet', {
                chart: {
                    type: 'line'
                },
                title: { text: 'No. of Matches Played' },
                xAxis: { type: 'datetime' },
                series: [{
                    name: 'Matches',
                    data: data.match_data
                }]
            });
        } else {
            console.error('Highcharts library is not loaded.');
        }
    })
    .catch(err => console.error('Error fetching match history:', err));
}

function fetchAndRenderAnime() {
    const searchAnimeElement = document.getElementById('search_anime');
    const animeEpisodeElement = document.getElementById('search_anime_episode');
    const animeEpisode = animeEpisodeElement ? animeEpisodeElement.value : '';
    const animeName = searchAnimeElement ? searchAnimeElement.value : '';

    const url = new URL('/admin/get_anime', window.location.origin);
    if (animeName) url.searchParams.append('search_anime', animeName);
    if (animeEpisode) url.searchParams.append('search_anime_episode', animeEpisode);

    fetch(url)
        .then(response => response.json())
        .then(data => {
            const animeTableBody = document.getElementById('anime-table-body');
            if (!animeTableBody) return;
            animeTableBody.innerHTML = '';

            data.animes.forEach(anime => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${anime.id}</td>
                    <td>${anime.anime_season}</td>
                    <td>${anime.ep_number}</td>
                    <td>
                        <button class="btn-primary user" onclick="openUpdateAnimeModal('${anime.id}', '${anime.ep_number}', '${anime.anime_season}', '${anime.video_url}')">Update</button>
                    </td>
                    <td>
                        <button class="btn-danger user" onclick="confirmDeleteAnimeModal('${anime.id}')">Delete</button>
                    </td>
                `;
                animeTableBody.appendChild(tr);
            }
        );
        if (data.animes.length === 0) {
            const animeTable = document.getElementById('anime-table-body');
            animeTableBody.innerHTML = '';
            if (animeTable) {
                const tr = document.createElement('h1');
                tr.style.height = '100%';
                tr.style.textAlign = 'center';
                tr.style.width = '100%';
                tr.textContent = 'No anime found';
                animeTableBody.appendChild(tr);
            }
        }
        console.log('hi');
    })
    .catch(err => console.error('Error fetching anime:', err));
}

function openAddAnimeModal() {
    document.getElementById("add-anime-modal").style.display = "block";
}

function closeAddAnimeModal() {
    document.getElementById("add-anime-modal").style.display = "none";
}

function submitAddAnimeForm() {
    const form = document.getElementById("add-anime-form");
    const formData = new FormData(form);

    fetch("/admin/add_anime", {
        method: "POST",
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showModal(data.message, "success");
            fetchAndRenderAnime();
            closeAddAnimeModal();
        } else if (data.error) {
            showModal(data.error, "error");
        } else {
            showModal("An unknown error occurred.", "error");
        }
    })
    .catch(error => {
        console.error("Error adding anime:", error);
        showModal("Error adding anime", "error");
    });
}

function confirmDeleteAnimeModal(id) {
    const deleteModal = document.getElementById('confirm-delete-anime-modal');
    deleteModal.dataset.id = id; 
    openModal('confirm-delete-anime-modal');
}

function deleteAnime() {
    const animeId = document.getElementById('confirm-delete-anime-modal').dataset.id;

    fetch(`/admin/delete_anime/${animeId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.message && !data.error) {
            showModal(data.message, 'success');
            fetchAndRenderAnime();
        } else {
            const msg = data.message || data.error || "An error occurred deleting anime.";
            showModal(msg, 'error');
        }
    })
    .catch(() => showModal('An unexpected error occurred. Please try again later.', 'error'))
    .finally(() => closeModal('confirm-delete-anime-modal'));
}

const modals = document.getElementsByClassName('esoteric-modal');
Array.from(modals).forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });
});

function updateAnime() {
    const animeId = document.getElementById('edit-anime-modal').dataset.id;
    const form = document.getElementById('editAnimeForm');
    const formData = new FormData(form);

    fetch(`/admin/update_anime/${animeId}`, {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showModal(data.message, 'success');
            fetchAndRenderAnime();
            closeModal('edit-anime-modal');
        } else if (data.error) {
            showModal(data.error, 'error');
        } else {
            showModal('An unknown error occurred.', 'error');
        }
    })
    .catch(error => {
        console.error('Error updating anime:', error);
        showModal('Error updating anime', 'error');
    });
}

const editAnimeForm = document.getElementById('editAnimeForm');
editAnimeForm.addEventListener('submit', function (event) {
    event.preventDefault();
    updateAnime();
});