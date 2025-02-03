document.addEventListener('DOMContentLoaded', () => {
    const socket = io('/', { transports: ['websocket'] });

    const miniChatMessages = document.getElementById("mini-chat-messages");
    const miniChatSend = document.getElementById("mini-chat-send");
    const miniChatInput = document.getElementById("mini-chat-input");

    socket.on('connect', () => {
        console.log('Connected to server');
        socket.emit('game_room_joined', { room: ROOM_CODE });
        socket.emit('load_game_information', { room: ROOM_CODE });
        get_game_information();
    });
    
    socket.on("mini_chat_message", (data) => {
        const { sender, message } = data;
        if (!message) {
            return;
        }
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
            msgDiv.style.fontSize = '1.8vh';
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

    document.getElementById('leave-room-btn').addEventListener('click', () => {
        window.location.href = '/arenaLobby';
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

    socket.on('game_end', (data) => {
        console.log('Game end event:', data);
        showModal(data.message, 'success');
    });

    socket.on('game_room_closed', (data) => {
        console.log('game_room_closed event:', data);
        showModal(data.message, 'error');
        window.location.href = '/arenaLobby';
    });

    function get_game_information() {
        fetch(`/spectator/information/${ROOM_CODE}`, {
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

    function impactChecker(card) {
        if (card.type == 'Impact' || card.type === 'Impact Monster') {
            return true;
        } 
    }
    
    function showModalWrapper() {
        document.getElementById('user-zones-modal-wrapper').style.display = 'flex';
    }
    function hideModalWrapper() {
        document.getElementById('user-zones-modal-wrapper').style.display = 'none';
    }

    const userSearchDropModal = document.getElementById("user-search-drop-modal");
    document.getElementById('player-drop-zone').addEventListener('click', () => {
        console.log('Player Drop Zone');
        showModalWrapper();
        userSearchDropModal.style.display = 'flex';
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
            } else if (button.closest('#user-search-soul-modal')) {
                document.getElementById('user-search-soul-modal').style.display = 'none';
            } else if (button.closest('#spell-modal')) {
                document.getElementById('spell-modal').style.display = 'none';
            }
            if (userSearchDeckModal.style.display === 'none' 
                && userSearchDropModal.style.display === 'none' 
                && document.getElementById('spell-modal').style.display === 'none' 
                && document.getElementById('user-search-soul-modal').style.display === 'none') {
                hideModalWrapper();
            }
        });
    });

    const oppoDrop = document.getElementById("opponent-search-drop-modal")
    document.getElementById('opponent-drop-zone').addEventListener("click", (e) => {
        console.log('Opponent Drop Zone');
        oppoDrop.style.display = "flex";
        document.getElementById('opponent-deck-modal-wrapper').style.display = 'flex';
    });

    oppoDrop.addEventListener("click", (e) => {
        if (e.target === oppoDrop) {
            oppoDrop.style.display = "none";
            document.getElementById('opponent-deck-modal-wrapper').style.display = 'flex';
        }
    });

    socket.on('phase_updated', (data) => {
        console.log('Phase Updated:', data.phase);
        socket.emit('spectator_phase_update', { room: ROOM_CODE });
    });

    socket.on('spectator_phase_updated', (data) => {
        console.log('Spectator Phase Updated:', data.phase);
        document.getElementById('opponent-game-phase-content').textContent = data.phase2;
        document.getElementById('user-game-phase-content').textContent = data.phase1;
    });

    socket.on('life_update', (data) => {
        socket.emit('spectator_life_update', { room: ROOM_CODE });
    });

    socket.on('spectator_life_updated', (data) => {
        document.getElementById('player-life-total').textContent = data.life1;
        document.getElementById('opponent-life-total').textContent = data.life2;
    });

    function attachHandCardListeners() {
        const allCards = document.querySelectorAll(".hand-card");
        allCards.forEach((oldElem) => {
            const newElem = oldElem.cloneNode(true);

            const cardObj = JSON.parse(oldElem.dataset.cardObj || '{}');

            newElem.addEventListener('mouseenter', () => {
                console.log('Mouse Enter');

                let cardData;
                try {
                    cardData = JSON.parse(newElem.dataset.cardObj);
                } catch (error) {
                    console.error('Failed to parse card data:', error);
                    return;
                }

                const cardModal = document.getElementById('card-info-overlay');
                cardModal.style.display = 'flex';

                const cardImage = document.getElementById('overlay-card-image');
                const cardDescription = document.getElementById('overlay-card-description');

                cardImage.innerHTML = "";
                cardDescription.innerHTML = "";
                cardDescription.style.overflow = 'auto';
                cardDescription.style.fontSize = '1.8vh';
                const img = document.createElement('img');
                img.src = cardData.image_url;
                img.alt = cardData.name;
                img.style.width = '100%';
                img.style.backgroundColor = 'none'
                if (impactChecker(cardData)) {
                    img.rotate = '90deg';
                    cardDescription.style.marginTop = '-25vh';
                    cardDescription.style.height = '60vh';
                } else {
                    cardDescription.style.marginTop = '0vh';
                    cardDescription.style.height = '35vh';
                    img.rotate = '0deg';
                }
                cardImage.appendChild(img);

                cardDescription.innerHTML = `
                    <h3>Card Name: ${cardData.name}</h3>
                    <p>World: ${cardData.world}</p>
                    <p>Type: ${cardData.type}</p>
                    <p>Card Rarity: ${cardData.rarity}</p>
                    <p>Power: ${cardData.power}</p>
                    <p>Defense: ${cardData.defense}</p>
                    <p>Critical: ${cardData.critical}</p>
                    <p>Size: ${cardData.size}</p>
                    <p>Attribute: ${cardData.attribute}</p>
                    <p>Ability: ${formatAbilityText(cardData.ability_effect)}</p>
                `
            });

            newElem.addEventListener('mouseleave', () => {
                console.log('Mouse Leave');
                const cardModal = document.getElementById('card-info-overlay');
                cardModal.style.display = 'none';
            });

            newElem.addEventListener('wheel', (e) => {
                e.preventDefault();
                console.log('Scrolling');
                const cardDescription = document.getElementById('overlay-card-description');
                if (cardDescription) {
                    cardDescription.scrollTop += e.deltaY;
                    cardDescription.scrollLeft += e.deltaX;
                }
            });

            if (cardObj.soul && cardObj.soul.length > 0) {
                const soulContainer = document.createElement('div');
                soulContainer.classList.add('soul-holder');
                const soulCount = document.createElement('p');
                soulCount.classList.add('soul-count');
                soulCount.textContent = cardObj.soul.length;

                soulCount.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    console.log('Soul Count Clicked');
                    showModalWrapper()
                    const soulModal = document.getElementById('user-search-soul-modal');
                    soulModal.style.display = 'flex';
                    const soulContent = document.getElementById('user-soul-content');
                    document.getElementById('soul-modal').textContent =`Soul of ${cardObj.name}`;
                    soulContent.innerHTML = '';
                    soulContent.dataset.hostCard = JSON.stringify(cardObj);

                    let fromZoneForSoul = 'soul';

                    cardObj.soul.forEach((soulCard) => {
                        const soulCardDiv = document.createElement('div');
                        soulCardDiv.classList.add('hand-card');
                        soulCardDiv.dataset.cardObj = JSON.stringify(soulCard);
                        soulCardDiv.dataset.fromZone = fromZoneForSoul;
                        soulCardDiv.draggable = false;
                        if (impactChecker(soulCard)) {
                            soulCardDiv.innerHTML = `
                            <img src="${soulCard.image_url}"
                                alt="${soulCard.name}"
                                class="impact-card"
                                
                                draggable="false" style="pointer-events: none;"/>
                            `;
                        } else {
                            soulCardDiv.innerHTML = `
                            <img src="${soulCard.image_url}"
                                alt="${soulCard.name}"
                                class="normal-card"
                                draggable="false" style="pointer-events: none;"/>
                            `;
                        }
                        soulContent.appendChild(soulCardDiv);

                        if (soulCard.owner != USERNAME) {
                            soulCardDiv.addEventListener('mouseenter', () => {
                                console.log('Mouse Enter');
                
                                let cardData;
                                try {
                                    cardData = JSON.parse(soulCardDiv.dataset.cardObj);
                                } catch (error) {
                                    console.error('Failed to parse card data:', error);
                                    return;
                                }
                
                                const cardModal = document.getElementById('card-info-overlay');
                                cardModal.style.display = 'flex';
                
                                const cardImage = document.getElementById('overlay-card-image');
                                const cardDescription = document.getElementById('overlay-card-description');
                
                                cardImage.innerHTML = "";
                                cardDescription.innerHTML = "";
                                cardDescription.scrollTop = 0;
                                cardDescription.style.overflow = 'auto';
                                cardDescription.style.fontSize = '1.8vh';
                                const img = document.createElement('img');
                                img.src = cardData.image_url;
                                img.alt = cardData.name;
                                img.style.width = '100%';
                                img.style.backgroundColor = 'none'
                                if (impactChecker(cardData)) {
                                    img.rotate = '90deg';
                                    cardDescription.style.marginTop = '-25vh';
                                    cardDescription.style.height = '60vh';
                                } else {
                                    cardDescription.style.marginTop = '0vh';
                                    cardDescription.style.height = '35vh';
                                    img.rotate = '0deg';
                                }
                                cardImage.appendChild(img);
                
                                cardDescription.innerHTML = `
                                    <h3>Card Name: ${cardData.name}</h3>
                                    <p>World: ${cardData.world}</p>
                                    <p>Type: ${cardData.type}</p>
                                    <p>Card Rarity: ${cardData.rarity}</p>
                                    <p>Power: ${cardData.power}</p>
                                    <p>Defense: ${cardData.defense}</p>
                                    <p>Critical: ${cardData.critical}</p>
                                    <p>Size: ${cardData.size}</p>
                                    <p>Attribute: ${cardData.attribute}</p>
                                    <p>Ability: ${formatAbilityText(cardData.ability_effect)}</p>
                                `
                            });
                            
                            soulCardDiv.addEventListener('wheel', (e) => {
                                e.preventDefault();
                                console.log('Scrolling');
                                const cardDescription = document.getElementById('overlay-card-description');
                                if (cardDescription) {
                                    cardDescription.scrollTop += e.deltaY;
                                    cardDescription.scrollLeft += e.deltaX;
                                }
                            });
                
                            soulCardDiv.addEventListener('mouseleave', () => {
                                console.log('Mouse Leave');
                                const cardModal = document.getElementById('card-info-overlay');
                                cardModal.style.display = 'none';
                            });
                        }
                    });
                });
                soulContainer.appendChild(soulCount);
                newElem.appendChild(soulContainer);
            }
            
            oldElem.parentNode.replaceChild(newElem, oldElem);
        });
    }

    const userSpellZone = document.getElementById("player-spell-zone");
    const opponentSpellZone = document.getElementById("opponent-spell-zone");

    opponentSpellZone.addEventListener("click", (e) => {
        console.log('Opponent Spell Zone');
        const opponentSpellsModal = document.getElementById('opponent-spells-modal');
        opponentSpellsModal.style.display = 'flex';
        opponentSpellsModal.classList.add('active');
    });

    const oppoSpell = document.getElementById("opponent-spells-modal");
    oppoSpell.addEventListener("click", (e) => {
        if (e.target === oppoSpell) {
            oppoSpell.style.display = "none";
        }
    });

    userSpellZone.addEventListener("click", (e) => {
        console.log('User Spell Zone');
        showModalWrapper() 
        document.getElementById('spell-modal').style.display = 'flex';
    });

    function renderCards(data) {
        console.log('Rendering Cards')
        console.log(data);
        const userState = data.user;
        const opponentState = data.opponent;

        userLife = userState.current_life;
        userGuageSize = userState.current_gauge_size;
        userHandSize = userState.current_hand_size;
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
        userLook = userState.look;

        opponentLife = opponentState.current_life;
        opponentGuageSize = opponentState.current_gauge_size;
        opponentHandSize = opponentState.current_hand_size;
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

        const playerDropzone = document.getElementById("player-drop-zone");
        playerDropzone.style.backgroundImage = '';
        playerDropzone.textContent = 'Drop Zone';
        if (userDropzone.length > 0) {
            playerDropzone.textContent = '';
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("hand-card");
            const card = userDropzone[userDropzone.length - 1];

            if (impactChecker(userDropzone[userDropzone.length - 1])) {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" 
                    class="impact-card" style="pointer-events: none; height: 5vw;">
                `;
            } else {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" 
                    class="normal-card" style="pointer-events: none; width: 5vw;">
                `;
            }
            playerDropzone.appendChild(cardDiv);
        }

        const opponentDropzoneDiv = document.getElementById("opponent-drop-zone");
        opponentDropzoneDiv.style.backgroundImage = '';
        opponentDropzoneDiv.textContent = 'Drop Zone';
        if (opponentDropzone.length > 0) {
            opponentDropzoneDiv.textContent = '';
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("hand-card");
            const card = opponentDropzone[opponentDropzone.length - 1];

            if (impactChecker(opponentDropzone[opponentDropzone.length - 1])) {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" 
                    class="impact-card" style="pointer-events: none; height: 5vw;">
                `;
            } else {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" 
                    class="normal-card" style="pointer-events: none; width: 5vw;">
                `;
            }

            opponentDropzoneDiv.appendChild(cardDiv);
        }

        const userDropDiv = document.getElementById("user-dropzone-content");
        userDropDiv.innerHTML = '';
        userDropzone.forEach((card) => {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(card);
            cardDiv.classList.add("hand-card");
            cardDiv.dataset.fromZone = "dropzone";
            cardDiv.draggable = false;
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
            cardDiv.dataset.cardObj = JSON.stringify(card);
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

        const opponentSpellDiv = document.getElementById("opponent-spells-content");
        const opponentSpellImg = document.querySelectorAll('.opponent-spell-zone-display');
        opponentSpellDiv.innerHTML = '';
        const opponentSpellArea = document.getElementById('opponent-spell-zone');
        if (opponentSpells.length > 0) {
            opponentSpellArea.innerHTML = '';
            opponentSpellImg.forEach(element => {
                element.style.display = 'none';
            });
            const latestSpell = opponentSpells[0];
            const spellImg = document.createElement('img');
            spellImg.src = latestSpell.image_url;
            spellImg.style.position = 'absolute';
            spellImg.alt = latestSpell.name;
            spellImg.draggable = false;
            if (impactChecker(latestSpell)) {
                spellImg.classList.add('impact-card');
            } else {
                spellImg.classList.add('normal-card');
                spellImg.style.width = '3vw';
                spellImg.style.aspectRatio = '2/3';
            }
            spellImg.style.borderRadius = '0.5vh';
            opponentSpellArea.appendChild(spellImg);
        } else {
            opponentSpellArea.innerHTML = `

                <img class="opponent-spell-zone-display" src="/img/circle.png" alt="Circle Image">
                <p class="opponent-spell-zone-display">Spells</p>
            `;
            opponentSpellImg.forEach(element => {
                element.style.display = 'flex';
            });
        }

        opponentSpells.forEach((card) => {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(card);
            cardDiv.classList.add("hand-card");
            if (impactChecker(card)) {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="impact-card" draggable="true">
                `;
                opponentSpellDiv.appendChild(cardDiv);
            } else {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="normal-card" draggable="true">
                `;
                opponentSpellDiv.appendChild(cardDiv);
            }
            if (card.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            } 

            if (opponentHighlight === userHighlight) {
                if (opponentHighlight && opponentHighlight === card.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (card.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
            } else if (card.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            }
        });

        const userSpellDiv = document.getElementById("user-spell-content");
        userSpellDiv.innerHTML = '';
        const userSpellImg = document.querySelectorAll('.spell-zone-display');
        const userSpellArea = document.getElementById('player-spell-zone');
        if (userSpells.length > 0) {
            userSpellArea.innerHTML = '';
            userSpellImg.forEach(element => {
                element.style.display = 'none';
            });
            const latestSpell = userSpells[0];
            let spellImg = document.createElement('img');
            spellImg.src = latestSpell.image_url;
            spellImg.style.position = 'absolute';
            spellImg.alt = latestSpell.name;
            spellImg.draggable = false;
            if (impactChecker(latestSpell)) {
                spellImg.classList.add('impact-card');
            } else {
                spellImg.classList.add('normal-card');
                spellImg.style.width = '3vw';
                spellImg.style.aspectRatio = '2/3';
            }
            spellImg.style.borderRadius = '0.5vh';
            userSpellArea.appendChild(spellImg);
        } else {
            userSpellArea.innerHTML = `
                <img class="spell-zone-display" src="/img/circle.png" alt="Circle Image">
                <p class="spell-zone-display">Spells</p>
                            `;
            userSpellImg.forEach(element => {
                element.style.display = 'flex';
            });
        }

        userSpells.forEach((card) => {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(card);
            cardDiv.classList.add("hand-card");
            cardDiv.dataset.fromZone = "spells";
            cardDiv.draggable = false;
            cardDiv.style.height = '10vh';
            if (impactChecker(card)) {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="impact-card" draggable="true">
                `;
                userSpellDiv.appendChild(cardDiv);
            } else {
                cardDiv.innerHTML = `
                    <img src="${card.image_url}" alt="${card.name}" class="normal-card" draggable="true">
                `;
                userSpellDiv.appendChild(cardDiv);
            }
            if (card.rest == true) {
                cardDiv.style.transform = "rotate(90deg)";
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            } 

            if (opponentHighlight === userHighlight) {
                if (opponentHighlight && opponentHighlight === card.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (card.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
            } else if (card.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            }
        });

        const userHandDiv = document.getElementById("user-hand-cards");
        userHandDiv.innerHTML = ''; 
        for (let i = 0; i < userHandSize; i++) {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("hand-card");
            cardDiv.classList.add("opponent-hand-card")
            cardDiv.draggable = false;
            cardDiv.style.rotate = '180deg';
            cardDiv.innerHTML = `
                <img src="/${PLAYER1_SLEEVE}" draggable="false" class="normal-card" >
            `;
            userHandDiv.appendChild(cardDiv);
        };
    
        const opponentHandDiv = document.getElementById("opponent-hand-cards");
        opponentHandDiv.innerHTML = ''; 
        for (let i = 0; i < opponentHandSize; i++) {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("hand-card");
            cardDiv.classList.add("opponent-hand-card")
            cardDiv.draggable = false;
            cardDiv.style.rotate = '180deg';
            cardDiv.innerHTML = `
                <img src="/${PLAYER2_SLEEVE}" draggable="false" class="normal-card" >
            `;
            opponentHandDiv.appendChild(cardDiv);
        };

        const userGuageDiv = document.getElementById("user-gauge-space");
        userGuageDiv.innerHTML = '';
        for (let i = 0; i < userGuageSize; i++) {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("gauge-card");
            cardDiv.draggable = false;
            cardDiv.innerHTML = `
                <img src="/${PLAYER1_SLEEVE}" draggable="false" class="normal-card">
            `;
            userGuageDiv.appendChild(cardDiv);
        }

        const opponentGuageDiv = document.getElementById("opponent-gauge-space");
        opponentGuageDiv.innerHTML = '';
        for (let i = 0; i < opponentGuageSize; i++) {
            const cardDiv = document.createElement("div");
            cardDiv.classList.add("gauge-card");
            cardDiv.draggable = false;
            cardDiv.innerHTML = `
                <img src="/${PLAYER2_SLEEVE}" draggable="false" class="normal-card">
            `;
            opponentGuageDiv.appendChild(cardDiv);
        }

        const userLeftSlot = document.getElementById("player-left");
        userLeftSlot.innerHTML = '';
        if (userLeftCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(userLeftCard);
            cardDiv.dataset.fromZone = "left";
            cardDiv.classList.add("hand-card");
            cardDiv.draggable = false;
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
                if (impactChecker(userLeftCard)) {
                    cardDiv.style.transform = "rotate(-90deg)";
                } else {
                    cardDiv.style.transform = "rotate(90deg)";
                }
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }

            if (userHighlight === opponentHighlight) {
                if (userHighlight && userHighlight === userLeftCard.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (userLeftCard.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            } else if (userLeftCard.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
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
            cardDiv.draggable = false;
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
                if (impactChecker(userCenterCard)) {
                    cardDiv.style.transform = "rotate(-90deg)";
                } else {
                    cardDiv.style.transform = "rotate(90deg)";
                }
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userHighlight === opponentHighlight) {
                if (userHighlight && userHighlight === userCenterCard.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (userCenterCard.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            } else if (userCenterCard.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
            }
        }

        const userRightSlot = document.getElementById("player-right");
        userRightSlot.innerHTML = '';
        if (userRightCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(userRightCard);
            cardDiv.classList.add("hand-card");
            cardDiv.dataset.fromZone = "right";
            cardDiv.draggable = false;
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
                if (impactChecker(userRightCard)) {
                    cardDiv.style.transform = "rotate(-90deg)";
                } else {
                    cardDiv.style.transform = "rotate(90deg)";
                }
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userHighlight === opponentHighlight) {
                if (userHighlight && userHighlight === userRightCard.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (userRightCard.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            } else if (userRightCard.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
            }
        }

        const userItemSlot = document.getElementById("player-flag-zone");
        userItemSlot.innerHTML = ""
        if (userItemCard) {
            const cardDiv = document.createElement("div");
            cardDiv.dataset.cardObj = JSON.stringify(userItemCard);
            cardDiv.classList.add("hand-card");
            cardDiv.dataset.fromZone = "item";
            cardDiv.draggable = false;

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
                if (impactChecker(userItemCard)) {
                    cardDiv.style.transform = "rotate(-90deg)";
                } else {
                    cardDiv.style.transform = "rotate(90deg)";
                }
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userHighlight === opponentHighlight) {
                if (userHighlight && userHighlight === userItemCard.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (userItemCard.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            } else if (userItemCard.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
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
                if (impactChecker(opponentLeftCard)) {
                    cardDiv.style.transform = "rotate(-90deg)";
                } else {
                    cardDiv.style.transform = "rotate(90deg)";
                }
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userHighlight === opponentHighlight) {
                if (userHighlight && userHighlight === opponentLeftCard.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (opponentLeftCard.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            } else if (opponentLeftCard.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
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
                if (impactChecker(opponentCenterCard)) {
                    cardDiv.style.transform = "rotate(-90deg)";
                } else {
                    cardDiv.style.transform = "rotate(90deg)";
                }
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userHighlight === opponentHighlight) {
                if (userHighlight && userHighlight === opponentCenterCard.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (opponentCenterCard.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            } else if (opponentCenterCard.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
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
                if (impactChecker(opponentRightCard)) {
                    cardDiv.style.transform = "rotate(-90deg)";
                } else {
                    cardDiv.style.transform = "rotate(90deg)";
                }
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userHighlight === opponentHighlight) {
                if (userHighlight && userHighlight === opponentRightCard.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (opponentRightCard.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            } else if (opponentRightCard.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
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
                if (impactChecker(opponentItemCard)) {
                    cardDiv.style.transform = "rotate(-90deg)";
                } else {
                    cardDiv.style.transform = "rotate(90deg)";
                }
            } else {
                cardDiv.style.transform = "rotate(0deg)";
            }
            if (userHighlight === opponentHighlight) {
                if (userHighlight && userHighlight === opponentItemCard.instance_id) {
                    const overlay = document.createElement('div');
                    overlay.classList.add('card-overlay', 'overlay-pink');
                    cardDiv.appendChild(overlay);
                }
            } else if (opponentItemCard.instance_id === userHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-blue');
                cardDiv.appendChild(overlay);
            } else if (opponentItemCard.instance_id === opponentHighlight) {
                const overlay = document.createElement('div');
                overlay.classList.add('card-overlay', 'overlay-red');
                cardDiv.appendChild(overlay);
            }
        }

        document.getElementById('user-search-soul-modal').style.display = 'none';

        attachHandCardListeners();
    }
});

document.addEventListener('contextmenu', (e) => {
    e.preventDefault();
});