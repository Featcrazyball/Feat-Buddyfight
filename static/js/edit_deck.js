document.addEventListener("DOMContentLoaded", function () {
    const unlockedCardsList = document.getElementById("unlocked-cards-list");
    const deckCardsList = document.getElementById("deck-cards-list");
    const saveDeckButton = document.getElementById("save-deck-btn");
    const buddyCardElement = document.getElementById("buddy-card");
    const setBuddyButton = document.getElementById("set-buddy-btn");

    let currentDeck = {};
    let unlockedCards = [];
    let buddyCardId = null;

    fetch("/edit_deck/get_deck")
        .then(response => response.json())
        .then(data => {
            const { deck, unlocked_cards } = data;

            unlockedCards = unlocked_cards;
            buddyCardId = deck.buddy_card_id;

            deck.cards.forEach(cardId => {
                const card = unlockedCards.find(c => c.id === cardId);
                if (card) {
                    if (!currentDeck[card.name]) {
                        currentDeck[card.name] = { cards: [], count: 0 };
                    }
                    currentDeck[card.name].cards.push(card);
                    currentDeck[card.name].count += 1;
                }
            });

            unlockedCards.forEach(card => {
                const cardItem = createCardElement(card);
                unlockedCardsList.appendChild(cardItem);
            });

            updateDeckCardsList();
            updateBuddyCardDisplay();
        })
        .catch(error => console.error("Error loading deck data:", error));

    saveDeckButton.addEventListener("click", function () {
        const cards = Object.values(currentDeck).flatMap(({ cards }) =>
            cards.map(card => card.id)
        );

        fetch("/edit_deck/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cards, buddy_card_id: buddyCardId })
        })
            .then(response => response.json())
            .then(data => {
                showModal(data.message, data.status);
            })
            .catch(error => {
                console.error("Error saving deck:", error);
                showModal("An error occurred while saving the deck.", "error");
            });
    });

    function createCardElement(card, count = 0) {
        if (!card) return;

        const cardItem = document.createElement("div");
        cardItem.classList.add(card.is_horizontal ? "card-horizontal-vertical" : "card-item");
        cardItem.dataset.cardId = card.id;
        cardItem.draggable = false;

        const cardImage = document.createElement("img");
        cardImage.src = card.image_url;
        cardImage.alt = card.name;
        cardImage.classList.add(card.is_horizontal ? "card-image-horizontal" : "card-image");
        cardItem.appendChild(cardImage);
        cardImage.draggable = false;

        if (count > 0) {
            const cardCount = document.createElement("div");
            cardCount.classList.add("card-count");
            cardCount.textContent = `x${count}`;
            cardItem.appendChild(cardCount);
        }

        if (card.type && card.type === "Monster") {
            const buddyBadge = document.createElement("div");
            buddyBadge.classList.add("buddy-badge");
            buddyBadge.textContent = "Buddy";
            if (buddyCardId === card.id) {
                buddyBadge.classList.add("active");
            }
            buddyBadge.addEventListener("click", function (e) {
                e.stopPropagation(); 
                setBuddy(card.id);
            });
            cardItem.appendChild(buddyBadge);
        }

        if (cardItem) {
            cardItem.addEventListener("click", function () {
                showCardModal(card);
            });
        }

        return cardItem;
    }

    function addCardToDeck(card) {
        if (!currentDeck[card.name]) {
            currentDeck[card.name] = { cards: [], count: 0 };
        }
        if (currentDeck[card.name].count < 4) {
            currentDeck[card.name].cards.push(card);
            currentDeck[card.name].count += 1;
            updateDeckCardsList();
        } else {
            showModal("You can only add up to 4 copies of cards with the same name.", "error");
        }
    }

    function removeCardFromDeck(card) {
        if (currentDeck[card.name] && currentDeck[card.name].count > 0) {
            currentDeck[card.name].cards.pop();
            currentDeck[card.name].count -= 1;
            if (currentDeck[card.name].count === 0) {
                delete currentDeck[card.name];
            }
            updateDeckCardsList();
        }
    }

    function setBuddy(cardId) {
        buddyCardId = cardId;
        updateBuddyCardDisplay();
    }

    function updateBuddyCardDisplay() {
        if (buddyCardId) {
            const buddyCard = unlockedCards.find(c => c.id === buddyCardId);
            if (buddyCard) {
                buddyCardElement.innerHTML = `
                    <div class="card-item" style="background-image: url(${buddyCard.image_url})">
                        <div class="buddy-badge active">Buddy</div>
                    </div>
                `;
            }
        } else {
            buddyCardElement.innerHTML = "<p>No Buddy Selected</p>";
        }
    }

    function showCardModal(card) {
        const modal = document.getElementById("card-modal");
        const cardInfo = document.getElementById("card-info");
        const addCardButton = document.getElementById("add-card-btn");
        const removeCardButton = document.getElementById("remove-card-btn");

        cardInfo.innerHTML = `
            <img src="${card.image_url}">
            <h3>${card.name}</h3>
            <p>Rarity: ${card.rarity}</p>
            <p>Type: ${card.type}</p>
            <p>World: ${card.world}</p>
            <p>Attributes: ${card.attribute}</p>
            <p>Size: ${card.size}</p>
            <p>Power: ${card.power}</p>
            <p>Defense: ${card.defense}</p>
            <p>Critical: ${card.critical}</p>
            <p>Ability: <br>${formatAbilityText(card.ability_effect)}</p>
        `;

        addCardButton.onclick = function () {
            addCardToDeck(card);
            modal.style.display = "none";
        };

        removeCardButton.onclick = function () {
            removeCardFromDeck(card);
            modal.style.display = "none";
        };

        setBuddyButton.onclick = function () {
            setBuddy(card.id);
            modal.style.display = "none";
        };

        modal.style.display = "flex";
    }

    const searchInput = document.getElementById('name');
    const searchButton = document.querySelector('.search-btn');

    searchButton.addEventListener('click', function (e) {
        e.preventDefault();
        const query = searchInput.value.trim();
        fetch(`/edit_deck/get_deck?name=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                const unlockedCardsList = document.getElementById('unlocked-cards-list');
                unlockedCardsList.innerHTML = ""; 

                data.unlocked_cards.forEach(card => {
                    const cardElement = createCardElement(card);
                    unlockedCardsList.appendChild(cardElement);
                });
            })
            .catch(error => console.error("Search Error:", error));
    });

    function updateDeckCardsList() {
        deckCardsList.innerHTML = "";

        Object.entries(currentDeck).forEach(([cardName, { cards, count }]) => {
            const cardElement = createCardElement(cards[0], count); 
            deckCardsList.appendChild(cardElement);
        });

        const totalCardCount = Object.values(currentDeck).reduce((sum, { count }) => sum + count, 0);
        const totalCountElement = document.getElementById("deck-total-count");
        totalCountElement.textContent = `Total Cards: ${totalCardCount}`;
    }
});

document.getElementById("card-modal").addEventListener("click", function (e) {
    if (e.target === this) this.style.display = "none";
});

document.getElementById("close-button").addEventListener("click", function (e) {
    if (e.target === this) document.getElementById("card-modal").style.display = "none";
});