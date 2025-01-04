document.querySelectorAll(".dynamic-form").forEach((form) => {
    form.addEventListener("submit", function (e) {
        e.preventDefault(); 

        const formData = new FormData(this); 
        const action = this.action; 

        fetch(action, {
            method: "POST",
            body: formData,
        })
            .then((response) => response.json())
            .then((data) => {
                showModal(data.message, data.status);
            })
            .catch((error) => {
                console.error("Error:", error);
                showModal("An error occurred. Please try again.", "error");
            });
    });
});