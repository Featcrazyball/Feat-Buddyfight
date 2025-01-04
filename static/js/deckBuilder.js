const flagToCSS = {
    "Star Dragon World": "StarDW",
    "Dragon World": "DragonWorld",
    "Darkness Dragon World": "DarknessDW",
    "Hero World": "HeroWorld",
    "Ancient World": "AncientWorld",
    "Danger World": "DangerWorld",
    "Dungeon World": "DungeonWorld",
    "Katana World": "KatanaWorld",
    "Magic World": "MagicWorld",
    "Dragon Ein": "DragonEin",
    "Dragon Zwei": "DragonZwei",
    "Parade of Hundred Demons": "ParadeOfHundredDemons",
    "Legend World": "LegendWorld",
    "Searing Executioners": "SearingExecutioners",
    "Divine Guardians": "DivineGuardians"
};

document.addEventListener("DOMContentLoaded", function () {
    const selectedDeck = document.querySelector(".deck-item.selected");
    if (selectedDeck) {
        const deckId = selectedDeck.dataset.deckId;
        const deckFlag = selectedDeck.dataset.deckFlag;
        const cssFlag = flagToCSS[deckFlag]; 

        if (!cssFlag) {
            console.error(`No CSS mapping found for flag: ${deckFlag}`);
            return;
        }

        document.querySelectorAll(".deck-item, .inner-banner, .inner-banner-border-fill").forEach((el) => {
            el.classList.remove("selected");
            el.style.borderColor = "";
            el.style.boxShadow = "";
        });

        document.querySelectorAll(".inner-banner-border-fill").forEach((el) => {
            el.style.backgroundColor = "";
        });

        selectedDeck.classList.add("selected");
        selectedDeck.style.borderColor = `var(--${cssFlag})`;
        selectedDeck.style.boxShadow = `4px 6px 15px var(--${cssFlag})`;

        const innerBanner = selectedDeck.querySelector(".inner-banner");
        const borderFill = selectedDeck.querySelector(".inner-banner-border-fill");

        if (innerBanner) {
            innerBanner.classList.add("selected");
            innerBanner.style.boxShadow = `inset 0 0 0 5px var(--${cssFlag})`;
        }
        if (borderFill) {
            borderFill.classList.add("selected");
            borderFill.style.backgroundColor = `var(--${cssFlag})`;
        }

        document.documentElement.style.setProperty("--dynamic-color", `var(--${cssFlag})`);
    }
});

document.querySelectorAll(".deck-item").forEach((deck) => {
    deck.addEventListener("click", function () {
        const deckId = this.dataset.deckId;
        const deckFlag = this.dataset.deckFlag;
        const cssFlag = flagToCSS[deckFlag]; 
        const action = `/select_deck/${deckId}`;

        if (!cssFlag) {
            console.error(`No CSS mapping found for flag: ${deckFlag}`);
            return;
        }

        fetch(action, {
            method: "POST",
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.status === "success") {
                    document.querySelectorAll(".deck-item, .inner-banner, .inner-banner-border-fill").forEach((el) => {
                        el.classList.remove("selected");
                        el.style.borderColor = "";
                        el.style.boxShadow = "";
                    });

                    document.querySelectorAll(".inner-banner-border-fill").forEach((el) => {
                        el.style.backgroundColor = "";
                    });

                    this.classList.add("selected");
                    this.style.borderColor = `var(--${cssFlag})`;
                    this.style.boxShadow = `4px 6px 15px var(--${cssFlag})`;

                    const innerBanner = this.querySelector(".inner-banner");
                    const borderFill = this.querySelector(".inner-banner-border-fill");

                    if (innerBanner) {
                        innerBanner.classList.add("selected");
                        innerBanner.style.boxShadow = `inset 0 0 0 5px var(--${cssFlag})`;
                    }
                    if (borderFill) {
                        borderFill.classList.add("selected");
                        borderFill.style.backgroundColor = `var(--${cssFlag})`;
                    }

                    document.documentElement.style.setProperty("--dynamic-color", `var(--${cssFlag})`);
                }
                showModal(data.message, data.status);
            })
            .catch((error) => {
                console.error("Error:", error);
                showModal("An error occurred. Please try again.", "error");
            });
    });
});

function addDeckModal() {
    const modal = document.getElementById('deck-container')
    modal.style.display = "flex";

    window.addEventListener("click", (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    });
};

function hideModal() {
    const modal = document.getElementById('deck-container')
    modal.style.display = "none";
}

document.addEventListener("DOMContentLoaded", function () {
    const selectedDeck = document.querySelector(".deck-item.selected");
    if (selectedDeck) {
        applyDeckSelectionStyles(selectedDeck);
    }

    document.querySelectorAll(".deck-item").forEach((deck) => {
        deck.addEventListener("click", function () {
            const deckId = this.dataset.deckId;
            const deckFlag = this.dataset.deckFlag;
            const cssFlag = flagToCSS[deckFlag];

            if (!cssFlag) {
                console.error(`No CSS mapping found for flag: ${deckFlag}`);
                return;
            }

            fetch(`/select_deck/${deckId}`, {
                method: "POST",
            })
                .then((response) => response.json())
                .then((data) => {
                    if (data.status === "success") {
                        resetDeckSelectionStyles();
                        applyDeckSelectionStyles(this);
                        showModal(data.message, "success");
                    } else {
                        showModal("Failed to select deck.", "error");
                    }
                })
                .catch(() => showModal("An error occurred. Please try again.", "error"));
        });
    });

    function applyDeckSelectionStyles(deck) {
        const deckFlag = deck.dataset.deckFlag;
        const cssFlag = flagToCSS[deckFlag];

        deck.classList.add("selected");
        deck.style.borderColor = `var(--${cssFlag})`;
        deck.style.boxShadow = `4px 6px 15px var(--${cssFlag})`;

        const innerBanner = deck.querySelector(".inner-banner");
        const borderFill = deck.querySelector(".inner-banner-border-fill");

        if (innerBanner) {
            innerBanner.classList.add("selected");
            innerBanner.style.boxShadow = `inset 0 0 0 5px var(--${cssFlag})`;
        }
        if (borderFill) {
            borderFill.style.backgroundColor = `var(--${cssFlag})`;
        }
    }

    function resetDeckSelectionStyles() {
        document.querySelectorAll(".deck-item, .inner-banner, .inner-banner-border-fill").forEach((el) => {
            el.classList.remove("selected");
            el.style.borderColor = "";
            el.style.boxShadow = "";
        });
    }

    const addDeckForm = document.getElementById("addDeck")

    addDeckForm.addEventListener("submit", function () {
        event.preventDefault(); 

        const formData = new FormData(this);

        fetch(this.action, {
            method: "POST",
            body: formData,
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.status === "success") {
                    showModal("Deck added successfully!", "success");
                    window.location.href = window.location.href;
                } else {
                    showModal(data.message || "Failed to add deck.", "error");
                }
            })
            .catch(() => {
                showModal("An unexpected error occurred. Please try again.", "error");
            });
    });

    document.getElementById("add-deck-btn").addEventListener("click", function () {
        const modal = document.getElementById("deck-container");
        modal.style.display = "flex";

        window.addEventListener("click", (event) => {
            if (event.target === modal) {
                modal.style.display = "none";
            }
        });
    });

    document.getElementById("cancel-deck").addEventListener("click", function () {
        const modal = document.getElementById("deck-container");
        modal.style.display = "none";
    });

    const deleteDeckButton = document.getElementById("delete-deck-btn");
    const confirmYesButton = document.getElementById("confirm-yess");
    const confirmNoButton = document.getElementById("confirm-no");
    const confirmationModal = document.getElementById("confirmation-modal");
    const editDeckButton = document.getElementById("edit-deck-btn")

    let selectedDeckId = null;

    deleteDeckButton.disabled = true;
    editDeckButton.disabled = true;

    document.querySelectorAll(".deck-item").forEach((deck) => {
        deck.addEventListener("click", function () {
            selectedDeckId = this.dataset.deckId;
            deleteDeckButton.disabled = false;
            editDeckButton.disabled = false;
        });
    });

    deleteDeckButton.addEventListener("click", function () {
        if (!selectedDeckId) {
            console.error("No deck selected for deletion.");
            return;
        }
        confirmationModal.classList.add("visible");
    });

    confirmYesButton.addEventListener("click", function () {
        fetch(`/deckBuilder/delete_deck/${selectedDeckId}`, {
            method: "POST",
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.status === "success") {
                    const deckElement = document.querySelector(`.deck-item[data-deck-id="${selectedDeckId}"]`);
                    if (deckElement) {
                        deckElement.remove();
                    }
                    deleteDeckButton.disabled = true;
                    showModal(data.message, "success");
                } else {
                    showModal(data.message || "Failed to delete deck.", "error");
                }
            })
            .catch(() => showModal("An unexpected error occurred. Please try again.", "error"))
            .finally(() => {
                confirmationModal.classList.remove("visible");
            });
    });

    confirmNoButton.addEventListener("click", function () {
        confirmationModal.classList.remove("visible");
    });
});