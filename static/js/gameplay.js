document.addEventListener('DOMContentLoaded', () => {
    const socket = io.connect('http://' + window.location.hostname + ':8000', { transports: ['websocket'] });

    socket.on('connect', () => {
        console.log('Connected to server');
        socket.emit('game_room_joined', { room: ROOM_CODE });
        socket.emit('load_game_information', { room: ROOM_CODE });
    });
    
    socket.on('error', (data) => {
        console.error('Error event received:', data);
        const message = data.message || 'An unknown error occurred';
        showModal(message, 'error');
    });

    socket.on('update_game_information', () => {
        get_game_information();
    });

    socket.on('mini_modal', (data) => {
        console.log('Mini Modal:', data);
        showModal(data.message, data.status);
    });

    let zonesBound = false;

    function attachHandCardListeners() {
        const allCards = document.querySelectorAll(".hand-card");
        allCards.forEach((oldElem) => {
            const newElem = oldElem.cloneNode(true);
    
            newElem.addEventListener("dragstart", (e) => {
                newElem.classList.add("dragging");
                const cardJson = newElem.dataset.cardObj;
                const fromZone = newElem.dataset.fromZone;
                newElem.style.opacity = "0.3";
                const payload = {
                    card: JSON.parse(cardJson),
                    from_zone: fromZone,
                };
                e.dataTransfer.setData("application/json", JSON.stringify(payload));
            });
    
            newElem.addEventListener("dragend", () => {
                newElem.classList.remove("dragging");
                newElem.style.opacity = "1";
            });

            newElem.addEventListener("click", (e) => {
                console.log('clicked card');
                e.stopPropagation(); 
                socket.emit('highlight_card', { room: ROOM_CODE, card: JSON.parse(newElem.dataset.cardObj) });
            });

            newElem.addEventListener("contextmenu", (e) => {
                console.log('right clicked card');
                e.preventDefault();
                socket.emit('card_rest_toggle', { room: ROOM_CODE, card: JSON.parse(newElem.dataset.cardObj), zone: newElem.dataset.fromZone });
            });

            newElem.addEventListener('mouseover', () => {
                newElem.style.cursor = 'grab'
            });

            newElem.addEventListener('mousedown', () => {
                newElem.style.cursor = 'grabing'
            });
    
            oldElem.parentNode.replaceChild(newElem, oldElem);
        });
    }

    function bindZoneListeners() {
        const allZones = document.querySelectorAll(`
            .player-monster-slot, 
            .player-zone,
            .player-mini-zone,
            .user-hand-cards,
            .user-gauge-space,
            .player-deck-modal-content
        `);
    
        allZones.forEach((zoneElem) => {
            zoneElem.addEventListener("dragover", (e) => {
                e.preventDefault();
            });
    
            zoneElem.addEventListener("drop", (e) => {
                e.preventDefault();
    
                const payloadJson = e.dataTransfer.getData("application/json");
                if (!payloadJson) return;
    
                const payload = JSON.parse(payloadJson);
                const cardData = payload.card;
                const fromZone = payload.from_zone;
                const toZone = zoneElem.dataset.zone;

                if (fromZone === toZone) return;
    
                socket.emit("card_move", {
                    room: ROOM_CODE,
                    card: cardData,
                    from_zone: fromZone,
                    to_zone: toZone,
                });
            });
        });
    }

    let userLife, opponentLife,
        userGuageSize, opponentGuageSize,
        userGuage, opponentGuage,
        userHandSize, opponentHandSize,
        userHand, opponentHand,
        userDeckList, opponentDeckList,
        userDeckListCount, opponentDeckListCount,
        userLeftCard, opponentLeftCard,
        userRightCard, opponentRightCard,
        userCenterCard, opponentCenterCard,
        userItemCard, opponentItemCard,
        userSpells, opponentSpells,
        userDropzone, opponentDropzone,
        userPhase, opponentPhase,
        userHighlight, opponentHighlight;

    // When the user first joins the room, fetch the initial game data
    if (sessionStorage.getItem('hasFetchedInitData') !== 'true') {
        fetch(`/gameplay/gameInitialisation/${ROOM_CODE}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error:", data.error);
                showModal('Failed to fetch data', 'error');
                return;
            }
            console.log("Fetched data on first join:", data);
            renderCards(data);
        })
        .catch(err => {
            console.error("Error:", err);
            showModal('Failed to fetch data', 'error');
        });
        sessionStorage.setItem('hasFetchedInitData', 'true');
    } else {
        get_game_information();
    }
 
    function get_game_information() {
        if (sessionStorage.getItem('hasFetchedInitData') === 'true') {
        fetch(`/gameplay/gameInformation/${ROOM_CODE}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error:", data.error);
                showModal('Failed to fetch data', 'error');
                return;
            }
            console.log('testing for get_game_information:', data);
            renderCards(data);
            });
        }
    }

    const miniChatMessages = document.getElementById("mini-chat-messages");
    const miniChatInput = document.getElementById("mini-chat-input");
    const miniChatSend = document.getElementById("mini-chat-send");

    const drawCardBtn = document.getElementById("draw-card");  
    const gaugeBtn = document.getElementById("top-deck-gauge");
    const shuffleBtn = document.getElementById("shuffle-deck");
    const searchDropBtn = document.getElementById("search-drop-zone");
    const searchDeckBtn = document.getElementById("search-deck");
    const topDeckSoulBtn = document.getElementById("top-deck-to-soul");
    const topDeckDropBtn = document.getElementById("top-deck-drop");
    const topDeckLookBtn = document.getElementById("top-deck-look");

    const lifeUpBtn = document.getElementById("life-up");
    const lifeDownBtn = document.getElementById("life-down");

    const userSearchDeckModal = document.getElementById("user-search-deck-modal");
    const userSearchDropModal = document.getElementById("user-search-drop-modal");
    function showModalWrapper() {
        document.getElementById('user-zones-modal-wrapper').style.display = 'flex';
    }
    function hideModalWrapper() {
        document.getElementById('user-zones-modal-wrapper').style.display = 'none';
    }

    // Show Deck Modal
    searchDeckBtn.addEventListener('click', function() {
        showModalWrapper();
        userSearchDeckModal.style.display = 'flex';
        socket.emit("search_deck_open", { room: ROOM_CODE });
    });

    // Show Dropzone Modal
    searchDropBtn.addEventListener('click', function() {
        showModalWrapper();
        userSearchDropModal.style.display = 'flex';
        socket.emit("search_dropzone_open", { room: ROOM_CODE });
    });

    const exitButtons = document.querySelectorAll('.exit-button');
    exitButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (button.closest('#user-search-deck-modal')) {
                userSearchDeckModal.style.display = 'none';
                socket.emit('search_deck_close', { room: ROOM_CODE });
            } else if (button.closest('#user-search-drop-modal')) {
                userSearchDropModal.style.display = 'none';
                socket.emit('search_dropzone_close', { room: ROOM_CODE });
            }
            if (userSearchDeckModal.style.display === 'none' && userSearchDropModal.style.display === 'none') {
                hideModalWrapper();
            }
        });
    });

    const oppoDrop = document.getElementById("opponent-search-drop-modal")
    document.getElementById('opponent-drop-zone').addEventListener("click", (e) => {
        console.log('Opponent Drop Zone');
        socket.emit("search_opponent_dropzone_open", { room: ROOM_CODE });
        oppoDrop.style.display = "flex";
        document.getElementById('opponent-deck-modal-wrapper').style.display = 'flex';
    });

    oppoDrop.addEventListener("click", (e) => {
        if (e.target === oppoDrop) {
            oppoDrop.style.display = "none";
            document.getElementById('opponent-deck-modal-wrapper').style.display = 'flex';
            socket.emit("search_opponent_dropzone_close", { room: ROOM_CODE });
        }
    });

    // Buttons
    drawCardBtn.addEventListener("click", () => {
        console.log('clicked draw card');
        document.getElementById("card-draw-modal").style.display = "flex";
    });

    gaugeBtn.addEventListener("click", () => {
        console.log('clicked gauge');
        document.getElementById("gauge-draw-modal").style.display = "flex";
    });

    const drawModal = document.getElementById("card-draw-modal");
    drawModal.addEventListener("click", (e) => {
        if (e.target === drawModal) {
            drawModal.style.display = "none";
        }
    });

    const gaugeModal = document.getElementById("gauge-draw-modal");
    gaugeModal.addEventListener("click", (e) => {
        if (e.target === gaugeModal) {
            gaugeModal.style.display = "none";
        }
    });

    shuffleBtn.addEventListener("click", () => {
        socket.emit("shuffle_deck", { room: ROOM_CODE });
        console.log('Shuffle Deck');
    });

    // Modals
    const cardDrawForm = document.getElementById("card-draw-form");
    cardDrawForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const drawCount = parseInt(document.getElementById("card-draw-amount").value, 10);
        socket.emit("draw_card", { room: ROOM_CODE, cards_drawn: drawCount });
        
        document.getElementById("card-draw-modal").classList.remove("active");
    });

    const gaugeForm = document.getElementById("gauge-draw-form");
    gaugeForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const gaugeAmount = parseInt(document.getElementById("gauge-draw-amount").value, 10);
        socket.emit("gauge_update", { room: ROOM_CODE, gauge_change: gaugeAmount });

        document.getElementById("gauge-draw-modal").classList.remove("active");
    });

    // Leave Room
    const leaveRoomBtn = document.getElementById("leave-room-btn");
    leaveRoomBtn.addEventListener("click", () => {
        socket.emit("leave_created_game_room", { room: ROOM_CODE });
        window.location.href = "/arenaLobby";
    });

    socket.on('game_end', (data) => {
        console.log('Game end event:', data);
        showModal(data.message, "success");
        currentRoomCode = null;
    });

    // Mini Chat [Not Working]
    socket.on("mini_chat_message", (data) => {
        const { sender, message } = data;
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message");
        if (sender === "System") {
            msgDiv.style.color = "red";
            msgDiv.style.fontStyle = "italic";
            msgDiv.style.fontWeight = "bold";
            msgDiv.style.border = "1px solid red";
            msgDiv.style.borderRadius = "5px";
            msgDiv.style.padding = "5px";
            msgDiv.style.textAlign = "center";
            msgDiv.style.backgroundColor = 'black';
        }
        msgDiv.textContent = `${sender}: ${message}`;
        miniChatMessages.appendChild(msgDiv);
        miniChatMessages.scrollTop = miniChatMessages.scrollHeight;
    });

    miniChatSend.addEventListener("click", () => {
        const msg = miniChatInput.value.trim();
        if (!msg) return;
        socket.emit("mini_chat_send", { room: ROOM_CODE, message: msg });
        miniChatInput.value = "";
    });

    miniChatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            miniChatSend.click();
        }
    });
      
    // Life Counter
    lifeUpBtn.addEventListener("click", () => {
        document.getElementById("player-life-total").textContent = parseInt(document.getElementById("player-life-total").textContent) + 1;
        socket.emit("life_increase", { room: ROOM_CODE });
    });

    lifeDownBtn.addEventListener("click", () => {
        document.getElementById("player-life-total").textContent = parseInt(document.getElementById("player-life-total").textContent) - 1;
        socket.emit("life_decrease", { room: ROOM_CODE });
    });

    socket.on('life_update', (data) => {
        console.log('Life update event:', data.current_life);
        opponentLife = data.current_life;
        document.getElementById("opponent-life-total").textContent = opponentLife;
    });

    // Phase Updater
    document.getElementById('user-game-phase').addEventListener('click', () => {
        console.log('Phase Updater Clicked');
        let state = document.getElementById('user-game-phase-content').textContent;
        if (state == 'Start Turn') {
            document.getElementById('user-game-phase-content').textContent = 'Draw Phase';
        } else if (state == 'Draw Phase') {
            document.getElementById('user-game-phase-content').textContent = 'Main Phase';
        } else if (state == 'Main Phase') {
            document.getElementById('user-game-phase-content').textContent = 'Attack Phase';
        } else if (state == 'Attack Phase') {
            document.getElementById('user-game-phase-content').textContent = 'End Phase';
        } else if (state == 'End Phase') {
            document.getElementById('user-game-phase-content').textContent = 'End Turn';
        } else if (state == 'End Turn') {
            document.getElementById('user-game-phase-content').textContent = 'Start Turn';
        }

        socket.emit('phase_update', { room: ROOM_CODE, phase: document.getElementById('user-game-phase-content').textContent });
    });

    socket.on('phase_updated', (data) => {
        console.log('Phase Updated:', data.phase);
        document.getElementById('opponent-game-phase-content').textContent = data.phase;
    });

    //  Buddy Calling
    userBuddy = document.getElementById("player-buddy-zone");
    userBuddy.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        socket.emit('buddy_call', { room: ROOM_CODE });  
    });

    function impactChecker(card) {
        if (card.type == 'Impact') {
            return true;
        } 
    }

    function renderCards(data) {
        console.log('Rendering Cards')
        console.log(data);
        const userState = data.user;
        const opponentState = data.opponent;

        userLife = userState.current_life;
        userGuageSize = userState.current_gauge_size;
        userGuage = userState.current_gauge;
        userHandSize = userState.current_hand_size;
        userHand = userState.current_hand;
        userDeckList = userState.deck_list;
        userDeckListCount = userState.current_deck_count;
        userLeftCard = userState.left;
        userCenterCard = userState.center;
        userRightCard = userState.right;
        userItemCard = userState.item;
        userSpells = userState.spells;
        userDropzone = userState.dropzone;
        userPhase = userState.current_phase;
        userHighlight = userState.highlighter;
        userBuddyRest = userState.buddy_rest;

        opponentLife = opponentState.current_life;
        opponentGuageSize = opponentState.current_gauge_size;
        opponentGuage = opponentState.current_gauge;
        opponentHandSize = opponentState.current_hand_size;
        opponentHand = opponentState.current_hand;
        opponentDeckList = opponentState.deck_list;
        opponentDeckListCount = opponentState.current_deck_count;
        opponentLeftCard = opponentState.left;
        opponentCenterCard = opponentState.center;
        opponentRightCard = opponentState.right;
        opponentItemCard = opponentState.item;
        opponentSpells = opponentState.spells;
        opponentDropzone = opponentState.dropzone;
        opponentPhase = opponentState.current_phase;
        opponentHighlight = opponentState.highlighter;
        opponentBuddyRest = opponentState.buddy_rest;

        document.getElementById("player-life-total").textContent = userLife;
        document.getElementById("opponent-life-total").textContent = opponentLife;

        document.getElementById("player-gauge-value").textContent = userGuageSize;
        document.getElementById("opponent-gauge-value").textContent = opponentGuageSize;

        document.getElementById('user-game-phase-content').textContent = userState.current_phase;
        document.getElementById('opponent-game-phase-content').textContent = opponentState.current_phase;

        userBuddy = document.getElementById("player-buddy-zone");
        if (userBuddyRest == true) {
            userBuddy.style.rotate = '90deg';
        } else if (userBuddyRest == false) {
            userBuddy.style.rotate = '0deg';
        }

        opponentBuddy = document.getElementById("opponent-buddy-zone");
        if (opponentBuddyRest == true) {
            opponentBuddy.style.rotate = '90deg';
        } else if (opponentBuddyRest == false) {
            opponentBuddy.style.rotate = '0deg';
        }

        const userDeckDiv = document.getElementById("player-deck-content");
        userDeckDiv.innerHTML = '';
        userDeckList.forEach((card) => {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(card);
            cardDiv.dataset.fromZone = "deck";
            cardDiv.classList.add("hand-card");
            cardDiv.draggable = true;
            if (impactChecker(card)) {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="impact-card" draggable="true">
                `;
                userDeckDiv.appendChild(cardDiv);
            } else {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="normal-card" draggable="true">
                `;
                userDeckDiv.appendChild(cardDiv); 
            }
        });

        userDropDiv = document.getElementById("user-dropzone-content");
        userDropDiv.innerHTML = '';
        userDropzone.forEach((card) => {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(card);
            cardDiv.classList.add("hand-card");
            cardDiv.dataset.fromZone = "dropzone";
            cardDiv.draggable = true;
            if (impactChecker(card)) {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="impact-card" draggable="true">
                `;
                userDropDiv.appendChild(cardDiv);
            } else {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="normal-card" draggable="true">
                `;
                userDropDiv.appendChild(cardDiv); 
            }
        });

        const opponentDropDiv = document.getElementById("opponent-dropzone-content");
        opponentDropDiv.innerHTML = '';
        opponentDropzone.forEach((card) => {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("hand-card");
            cardDiv.draggable = false;
            if (impactChecker(card)) {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="impact-card" draggable="true">
                `;
                opponentDropDiv.appendChild(cardDiv);
            } else {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="normal-card" draggable="true">
                `;
                opponentDropDiv.appendChild(cardDiv); 
            }
        });

        const userHandDiv = document.getElementById("user-hand-cards");
        userHandDiv.innerHTML = ''; 
        userHand.forEach((card) => {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(card);
            cardDiv.dataset.fromZone = "hand";
            cardDiv.classList.add("hand-card");
            cardDiv.draggable = true;
            if (impactChecker(card)) {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="impact-card" draggable="true">
                `;
                userHandDiv.appendChild(cardDiv);
            } else {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="normal-card" draggable="true">
                `;
                userHandDiv.appendChild(cardDiv); 
            }
        });
    
        const opponentHandDiv = document.getElementById("opponent-hand-cards");
        opponentHandDiv.innerHTML = ''; 
        opponentHand.forEach(() => {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("hand-card");
            cardDiv.draggable = false;
            cardDiv.style.rotate = '180deg';
            cardDiv.innerHTML = `
                <img src="/${OPPONENT_SLEEVE}" draggable="false" class="normal-card" >
            `;
            opponentHandDiv.appendChild(cardDiv);
        });

        const userGuageDiv = document.getElementById("user-gauge-space");
        userGuageDiv.innerHTML = '';
        userGuage.forEach((card) => {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardId = card;
            cardDiv.classList.add("gauge-card");
            cardDiv.draggable = false;
            cardDiv.innerHTML = `
                <img src="/${USER_SLEEVE}" draggable="false" class="normal-card">
            `;
            userGuageDiv.appendChild(cardDiv);
        });

        const opponentGuageDiv = document.getElementById("opponent-gauge-space");
        opponentGuageDiv.innerHTML = '';
        opponentGuage.forEach(() => {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("gauge-card");
            cardDiv.draggable = false;
            cardDiv.innerHTML = `
                <img src="/${OPPONENT_SLEEVE}" draggable="false" class="normal-card">
            `;
            opponentGuageDiv.appendChild(cardDiv);
        });

        const userLeftSlot = document.getElementById("player-left");
        userLeftSlot.innerHTML = '';
        if (userLeftCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(userLeftCard);
            cardDiv.dataset.fromZone = "left";
            cardDiv.classList.add("hand-card");
            cardDiv.draggable = true;
            if (impactChecker(userLeftCard)) {
                cardDiv.innerHTML = `
                    <img src="${userLeftCard.image_url}" alt="${userLeftCard.name}" 
                    class="impact-card" draggable="true" style="pointer-events: auto;">
                `;
            } else {
                cardDiv.innerHTML = `
                    <img src="${userLeftCard.image_url}" alt="${userLeftCard.name}" 
                    class="normal-card" draggable="true" style="pointer-events: auto;">
                `;
            }
            if (userLeftCard.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }

            if (userLeftCard.id === userHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid blue"; 
                }
            } else if (userLeftCard.id === opponentHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid red";
                }
            } else {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "none";
                }
            }
            userLeftSlot.appendChild(cardDiv);
        }

        const userCenterSlot = document.getElementById("player-center");
        userCenterSlot.innerHTML = '';
        if (userCenterCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(userCenterCard);
            cardDiv.dataset.fromZone = "center";
            cardDiv.classList.add("hand-card");
            cardDiv.draggable = true;
            if (impactChecker(userCenterCard)) {
                cardDiv.innerHTML = `
                    <img src="${userCenterCard.image_url}" alt="${userCenterCard.name}" 
                    class="impact-card" draggable="true" style="pointer-events: none;">
                `;
                userCenterSlot.appendChild(cardDiv);
            } else {
                cardDiv.innerHTML = `
                    <img src="${userCenterCard.image_url}" alt="${userCenterCard.name}" 
                    class="normal-card" draggable="true" style="pointer-events: none;">
                `;
                userCenterSlot.appendChild(cardDiv);
            }
            if (userCenterCard.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userCenterCard.id === userHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid blue"; 
                }
            } else if (userCenterCard.id === opponentHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid red";
                }
            } else {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "none";
                }
            }
        }

        const userRightSlot = document.getElementById("player-right");
        userRightSlot.innerHTML = '';
        if (userRightCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(userRightCard);
            cardDiv.classList.add("hand-card");
            cardDiv.dataset.fromZone = "right";
            cardDiv.draggable = true;
            if (impactChecker(userRightCard)) {
                cardDiv.innerHTML = `
                    <img src="${userRightCard.image_url}" alt="${userRightCard.name}" 
                    class="impact-card" draggable="true" style="pointer-events: none;">
                `;
                userRightSlot.appendChild(cardDiv);
            } else {
                cardDiv.innerHTML = `
                    <img src="${userRightCard.image_url}" alt="${userRightCard.name}" 
                    class="normal-card" draggable="true" style="pointer-events: none;">
                `;
                userRightSlot.appendChild(cardDiv);
            }
            if (userRightCard.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userRightCard.id === userHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid blue"; 
                }
            } else if (userRightCard.id === opponentHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid red";
                }
            } else {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "none";
                }
            }
        }

        const userItemSlot = document.getElementById("player-flag-zone");
        userItemSlot.innerHTML = ""
        if (userItemCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(userItemCard);
            cardDiv.classList.add("hand-card");
            cardDiv.dataset.fromZone = "item";
            cardDiv.draggable = true;

            cardDiv.style.position = "relative";
            cardDiv.style.zIndex = "2";
            cardDiv.style.top = "0";
            cardDiv.style.left = "0";
        
            if (impactChecker(userItemCard)) {
                cardDiv.innerHTML = `
                <img src="${userItemCard.image_url}"
                    alt="${userItemCard.name}"
                    class="impact-card"
                    draggable="false" style="pointer-events: auto;"/>
                `;
            } else {
                cardDiv.innerHTML = `
                <img src="${userItemCard.image_url}"
                    alt="${userItemCard.name}"
                    class="normal-card"
                    draggable="false" style="pointer-events: auto;" />
                `;
            }
            userItemSlot.appendChild(cardDiv);
            if (userItemCard.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userItemCard.id === userHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid blue"; 
                }
            } else if (userItemCard.id === opponentHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid red";
                }
            } else {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "none";
                }
            }
        }

        const opponentLeftSlot = document.getElementById("opponent-left");
        opponentLeftSlot.innerHTML = '';
        if (opponentLeftCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(opponentLeftCard);
            cardDiv.classList.add("hand-card");

            cardDiv.style.position = "relative";
            cardDiv.style.zIndex = "2";
            cardDiv.style.top = "0";
            cardDiv.style.left = "0";
            cardDiv.style.transform = "rotate(180deg)";
        
            if (impactChecker(opponentLeftCard)) {
                cardDiv.innerHTML = `
                <img src="${opponentLeftCard.image_url}"
                    alt="${opponentLeftCard.name}"
                    class="impact-card"
                    draggable="false" style="pointer-events: none;"/>
                `;
            } else {
                cardDiv.innerHTML = `
                <img src="${opponentLeftCard.image_url}"
                    alt="${opponentLeftCard.name}"
                    class="normal-card"
                    draggable="false" style="pointer-events: none;"/>
                `;
            }
            opponentLeftSlot.appendChild(cardDiv);
            if (opponentLeftCard.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (opponentLeftCard.id === userHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid blue"; 
                }
            } else if (opponentLeftCard.id === opponentHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid red";
                }
            } else {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "none";
                }
            }
        }

        const opponentCenterSlot = document.getElementById("opponent-center");
        opponentCenterSlot.innerHTML = '';
        if (opponentCenterCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(opponentCenterCard);
            cardDiv.classList.add("hand-card");

            cardDiv.style.position = "relative";
            cardDiv.style.zIndex = "2";
            cardDiv.style.top = "0";
            cardDiv.style.left = "0";
            cardDiv.style.transform = "rotate(180deg)";
        
            if (impactChecker(opponentCenterCard)) {
                cardDiv.innerHTML = `
                <img src="${opponentCenterCard.image_url}"
                    alt="${opponentCenterCard.name}"
                    class="impact-card"
                    draggable="false" style="pointer-events: none;"/>
                `;
            } else {
                cardDiv.innerHTML = `
                <img src="${opponentCenterCard.image_url}"
                    alt="${opponentCenterCard.name}"
                    class="normal-card"
                    draggable="false" style="pointer-events: none;"/>
                `;
            }
            opponentCenterSlot.appendChild(cardDiv);
            if (opponentCenterCard.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (opponentCenterCard.id === userHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid blue"; 
                }
            } else if (opponentCenterCard.id === opponentHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid red";
                }
            } else {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "none";
                }
            }
        }

        const opponentRightSlot = document.getElementById("opponent-right");
        opponentRightSlot.innerHTML = '';
        if (opponentRightCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(opponentRightCard);
            cardDiv.classList.add("hand-card");

            cardDiv.style.position = "relative";
            cardDiv.style.zIndex = "2";
            cardDiv.style.top = "0";
            cardDiv.style.left = "0";
            cardDiv.style.transform = "rotate(180deg)";
        
            if (impactChecker(opponentRightCard)) {
                cardDiv.innerHTML = `
                <img src="${opponentRightCard.image_url}"
                    alt="${opponentRightCard.name}"
                    class="impact-card"
                    draggable="false" style="pointer-events: none;"/>
                `;
            } else {
                cardDiv.innerHTML = `
                <img src="${opponentRightCard.image_url}"
                    alt="${opponentRightCard.name}"
                    class="normal-card"
                    draggable="false" style="pointer-events: none;"/>
                `;
            }
            opponentRightSlot.appendChild(cardDiv);
            if (opponentRightCard.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (opponentRightCard.id === userHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid blue"; 
                }
            } else if (opponentRightCard.id === opponentHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid red";
                }
            } else {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "none";
                }
            }
        }

        const opponentItemSlot = document.getElementById("opponent-flag-zone");
        opponentItemSlot.innerHTML = ""
        if (opponentItemCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(opponentItemCard);
            cardDiv.classList.add("hand-card");

            cardDiv.style.position = "relative";
            cardDiv.style.zIndex = "2";
            cardDiv.style.top = "0";
            cardDiv.style.left = "0";
            cardDiv.style.rotate = '180deg';
        
            if (impactChecker(opponentItemCard)) {
                cardDiv.innerHTML = `
                <img src="${opponentItemCard.image_url}"
                    alt="${opponentItemCard.name}"
                    class="impact-card"
                    draggable="false" style="pointer-events: none;"/>
                `;
            } else {
                cardDiv.innerHTML = `
                <img src="${opponentItemCard.image_url}"
                    alt="${opponentItemCard.name}"
                    class="normal-card"
                    draggable="false" style="pointer-events: none;"/>
                `;
            }
            opponentItemSlot.appendChild(cardDiv);
            if (opponentItemCard.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (opponentItemCard.id === userHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid blue"; 
                }
            } else if (opponentItemCard.id === opponentHighlight) {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "2px solid red";
                }
            } else {
                const img = cardDiv.querySelector('img');
                if (img) {
                  img.style.outline = "none";
                }
            }
        }

        attachHandCardListeners();
        if (!zonesBound) {
            bindZoneListeners();
            zonesBound = true;
        }
    }
});