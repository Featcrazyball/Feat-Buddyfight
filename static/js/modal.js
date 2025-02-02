function showModal(message, status) {
    const modal = document.getElementById("modal");
    const modalMessage = document.getElementById("modal-message");
    const modalContent = document.querySelector(".modal-content");
    const closeButton = document.querySelector(".close-button");

    modalMessage.innerHTML = `<span class="${status}">${message}</span>`;
    modal.style.display = "block";

    if (status === "success") {
        modalContent.classList.remove("error");
        modalContent.classList.add("success");
    } else if (status === "error") {
        modalContent.classList.remove("success");
        modalContent.classList.add("error");
    }

    window.addEventListener("click", (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    });

    closeButton.addEventListener("click", () => {
        console.log("close button clicked");
        modal.style.display = "none";
    });
}