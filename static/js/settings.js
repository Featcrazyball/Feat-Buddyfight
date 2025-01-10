document.getElementById('report-type').addEventListener('change', function () {
    const userReportSection = document.getElementById('user-report-section');
    const userBeingReportedInput = document.getElementById('user_being_reported');

    if (this.value === 'User Report') {
        userReportSection.style.display = 'block';
        userBeingReportedInput.setAttribute('required', 'required');
    } else {
        userReportSection.style.display = 'none';
        userBeingReportedInput.removeAttribute('required'); 
    }
});

document.getElementById('type').dispatchEvent(new Event('change'));

function showDeleteAccountModal() {
    const modal = document.getElementById('delete-account-modal');
    modal.classList.add('visible');
    modal.classList.remove('hidden');
}

function hideDeleteAccountModal() {
    const modal = document.getElementById('delete-account-modal');
    modal.classList.remove('visible');
    modal.classList.add('hidden');
}
window.onclick = function(event) {
    const modal = document.getElementById('delete-account-modal');
    if (event.target === modal) {
        hideDeleteAccountModal();
    }
};

function submitProfilePicture() {
    const form = document.getElementById("profilePictureForm");
    const formData = new FormData(form);

    fetch("/update_profile_picture", {
        method: "POST",
        body: formData,
    })
        .then((response) => response.json())
        .then((data) => {
            showModal(data.message, data.status);

            if (data.status === "success") {
                const profileImg = document.getElementById("profile-picture");
                profileImg.src = data.image_path;
            }
        })
        .catch((error) => {
            console.error("Error:", error);
            showModal("An error occurred. Please try again.", "error");
        });
}

