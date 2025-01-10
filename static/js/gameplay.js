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

    // Variables to store game state
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
        userLeftSoul, opponentLeftSoul,
        userCenterSoul, opponentCenterSoul,
        userRightSoul, opponentRightSoul,
        userItemSoul, opponentItemSoul,
        userSpells, opponentSpells,
        userDropzone, opponentDropzone,
        userLeftRest, opponentLeftRest,
        userRightRest, opponentRightRest,
        userCenterRest, opponentCenterRest,
        userItemRest, opponentItemRest,
        userLeftSoulCount, opponentLeftSoulCount,
        userCenterSoulCount, opponentCenterSoulCount,
        userRightSoulCount, opponentRightSoulCount,
        userItemSoulCount, opponentItemSoulCount;

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
            renderCards(data);
            });
        }
    }

    const miniChatMessages = document.getElementById("mini-chat-messages");
    const miniChatInput = document.getElementById("mini-chat-input");
    const miniChatSend = document.getElementById("mini-chat-send");

    const playerLifeTotal = document.getElementById("player-life-total");
    const opponentLifeTotal = document.getElementById("opponent-life-total");
    const lifeUpBtn = document.getElementById("life-up");
    const lifeDownBtn = document.getElementById("life-down");

    // const shuffleDeckBtn = document.getElementById("shuffle-deck");
    // const searchDeckBtn = document.getElementById("search-deck");
    // const topDeckToSoulBtn = document.getElementById("top-deck-to-soul");
    // const topDeckDropBtn = document.getElementById("top-deck-drop");
    // const topDeckRevealBtn = document.getElementById("top-deck-reveal");
    // const topDeckGaugeBtn = document.getElementById("top-deck-gauge");
    // const drawCardBtn = document.getElementById("draw-card");
    // const gaugeMinusBtn = document.getElementById("gauge-minus");

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
        userLeftSoul = userState.left_soul;
        userCenterSoul = userState.center_soul;
        userRightSoul = userState.right_soul;
        userItemSoul = userState.item_soul;
        userSpells = userState.spells;
        userDropzone = userState.dropzone;
        userLeftRest = userState['left-rest'];
        userCenterRest = userState['center-rest'];
        userRightRest = userState['right-rest'];
        userItemRest = userState['item-rest'];
        userLeftSoulCount = userState.left_soul.length;
        userCenterSoulCount = userState.center_soul.length;
        userRightSoulCount = userState.right_soul.length;
        userItemSoulCount = userState.item_soul.length;

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
        opponentLeftSoul = opponentState.left_soul;
        opponentCenterSoul = opponentState.center_soul;
        opponentRightSoul = opponentState.right_soul;
        opponentItemSoul = opponentState.item_soul;
        opponentSpells = opponentState.spells;
        opponentDropzone = opponentState.dropzone;
        opponentLeftRest = opponentState['left-rest'];
        opponentCenterRest = opponentState['center-rest'];
        opponentRightRest = opponentState['right-rest'];
        opponentItemRest = opponentState['item-rest'];
        opponentLeftSoulCount = opponentState.left_soul.length;
        opponentCenterSoulCount = opponentState.center_soul.length;
        opponentRightSoulCount = opponentState.right_soul.length;
        opponentItemSoulCount = opponentState.item_soul.length;

        // Example of using the fetched data
        document.getElementById("player-life-total").textContent = userLife;
        document.getElementById("opponent-life-total").textContent = opponentLife;

        document.getElementById("player-gauge-value").textContent = userGuageSize;
        document.getElementById("opponent-gauge-value").textContent = opponentGuageSize;

        document.getElementById('user-game-phase-content').textContent = userState.current_phase;
        document.getElementById('opponent-game-phase-content').textContent = opponentState.current_phase;

        const userHandDiv = document.getElementById("user-hand-cards");
        userHandDiv.innerHTML = ''; // Clear existing cards
        userHand.forEach(card => {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("hand-card"); // Use new hand-card class
            cardDiv.draggable = true;
            cardDiv.innerHTML = `
                <img src="${card.image_url}" alt="${card.name}" draggable="false">
            `;
            userHandDiv.appendChild(cardDiv);
        });
    
        const opponentHandDiv = document.getElementById("opponent-hand-cards");
        opponentHandDiv.innerHTML = ''; // Clear existing cards
        opponentHand.forEach(() => {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("hand-card"); // Use new hand-card class
            cardDiv.draggable = false;
            cardDiv.innerHTML = `
                <img src="/${OPPONENT_SLEEVE}" draggable="false">
            `;
            opponentHandDiv.appendChild(cardDiv);
        });

        const userGuageDiv = document.getElementById("user-gauge-space");
        userGuage.forEach(() => {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("gauge-card");
            cardDiv.draggable = false;
            cardDiv.innerHTML = `
                <img src="/${USER_SLEEVE}" draggable="false">
            `;
            userGuageDiv.appendChild(cardDiv);
        });

        const opponentGuageDiv = document.getElementById("opponent-gauge-space");
        opponentGuage.forEach(() => {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("gauge-card");
            cardDiv.draggable = false;
            cardDiv.innerHTML = `
                <img src="/${OPPONENT_SLEEVE}" draggable="false">
            `;
            opponentGuageDiv.appendChild(cardDiv);
        });
    }
});