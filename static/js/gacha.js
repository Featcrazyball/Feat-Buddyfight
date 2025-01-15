document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".tab");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const pull1xButtons = document.querySelectorAll(".pull-1x");
    const pull10xButtons = document.querySelectorAll(".pull-10x");
    const grayOverlay = document.getElementById("gray-overlay");
    const cardsDisplay = document.getElementById("cards-display");
    const video = document.getElementById("gacha-video");
    const ticketHeader = document.getElementById("header-tickets");

    let selectedWorld = null; 

    tabs.forEach((tab, index) => {
        tab.style.opacity = 0;
        tab.style.transform = "translateX(-50px)";
        setTimeout(() => {
            tab.style.transition = "opacity 0.5s ease, transform 0.5s ease";
            tab.style.opacity = 1;
            tab.style.transform = "translateX(0)";
        }, index * 100);

        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tabPanels.forEach(panel => panel.classList.remove("active"));

            tab.classList.add("active");
            selectedWorld = tab.alt === "All" ? null : tab.alt;
            document.getElementById(tab.dataset.tab).classList.add("active");
        });
    });

    async function fetchTicketCount() {
        try {
            const response = await fetch("/gacha/tickets", {
                method: "GET",
                headers: { "Content-Type": "application/json" },
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch ticket count. Status: ${response.status}`);
            }

            const data = await response.json();
            ticketHeader.textContent = `${data.tickets} Tickets`;
        } catch (error) {
            console.error("Error fetching ticket count:", error);
        }
    }

    fetchTicketCount();

    function disableButtonWithTimer(button, seconds) {
        button.disabled = true;
        button.style.filter = "grayscale(100%)";

        const timerOverlay = document.createElement("div");
        timerOverlay.className = "button-timer";
        timerOverlay.textContent = seconds;
        button.appendChild(timerOverlay);
        button.style.position = "relative";

        const interval = setInterval(() => {
            seconds--;
            timerOverlay.textContent = seconds;

            if (seconds <= 0) {
                clearInterval(interval);
                button.disabled = false;
                button.style.filter = "none";
                timerOverlay.remove();
            }
        }, 1000);
    }

    async function handlePull(type, button) {
        try {
            const response = await fetch("/gacha/tickets", {
                method: "GET",
                headers: { "Content-Type": "application/json" },
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch ticket count. Status: ${response.status}`);
            }

            const data = await response.json();

            const ticketsRequired = type === "10x" ? 10 : 1;
            if (data.tickets < ticketsRequired) {
                showModal("Not enough tickets!", "error");
                return;
            }

            disableButtonWithTimer(button, 5);

            if (type === "10x") {
                video.currentTime = 0;
                video.classList.remove("hidden");
                video.play();

                await new Promise(resolve => {
                    video.onended = resolve;
                    video.addEventListener("click", () => {
                        video.pause();
                        resolve();
                    });
                });

                video.classList.add("hidden");
            }

            const pullResponse = await fetch("/gacha/pull", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ type, world: selectedWorld }),
            });

            if (!pullResponse.ok) {
                const errorData = await pullResponse.json();
                showModal(errorData.message, "error");
                return;
            }

            const pullData = await pullResponse.json();

            if (pullData.status === "success") {
                showPulledCards(pullData.cards, pullData.tickets);
                updateTicketDisplay(pullData.current_tickets);
            } else {
                console.error(pullData.message);
            }
        } catch (error) {
            console.error(`Error in ${type} pull:`, error);
        }
    }

    function showPulledCards(cards, tickets) {
        cardsDisplay.innerHTML = "";
        grayOverlay.classList.remove("hidden");

        const cardContainer = document.createElement("div");
        cardContainer.className = "card-container";

        let row;
        cards.forEach((card, index) => {
            if (index % 5 === 0) {
                row = document.createElement("div");
                row.className = "card-row";
                cardContainer.appendChild(row);
            }

            const cardElement = document.createElement("div");
            cardElement.classList.add(card.is_horizontal ? "card-horizontal-vertical" : "card-item");
            cardElement.dataset.cardId = card.id;

            const cardImage = document.createElement("img");
            cardImage.src = card.image_url;
            cardImage.alt = card.name;
            cardImage.classList.add(card.is_horizontal ? "card-image-horizontal" : "card-image");
            cardElement.appendChild(cardImage);

            row.appendChild(cardElement);

            cardElement.style.transform = "scale(0)";
            setTimeout(() => {
                cardElement.style.transition = "transform 0.5s ease";
                cardElement.style.transform = "scale(1)";
            }, index * 300);
        });

        cardsDisplay.appendChild(cardContainer);

        if (tickets) {
            const ticketInfo = document.createElement("div");
            ticketInfo.style.width = "100%";
            ticketInfo.style.textAlign = "center";
            ticketInfo.className = "ticket-info";
            ticketInfo.textContent = `You gained ${tickets} tickets for duplicate cards!`;
            cardsDisplay.appendChild(ticketInfo);
        }

        grayOverlay.addEventListener("click", () => {
            grayOverlay.classList.add("hidden");
        });
    }

    function updateTicketDisplay(tickets) {
        const ticketDisplay = document.getElementById("header-tickets");
        ticketDisplay.textContent = `${tickets} Tickets`;
    }

    pull1xButtons.forEach(button => {
        button.addEventListener("click", () => handlePull("1x", button));
    });

    pull10xButtons.forEach(button => {
        button.addEventListener("click", () => handlePull("10x", button));
    });
});

