document.addEventListener("DOMContentLoaded", () => {
    // Ensure default tabs act as buttons and switch rooms on click
    document.querySelectorAll(".tablinks").forEach(btn => {
        btn.setAttribute("type", "button");
        btn.addEventListener("click", () => {
            switchRoom(btn.dataset.tab);
        });
    });

    const tabsContainer = document.querySelector(".tabs");
    const tabContents = document.querySelectorAll(".tabcontent");
    const messageInput = document.getElementById("messageInput");
    const sendMessageButton = document.getElementById("sendMessage");
    const leaveRoomButton = document.getElementById("leaveRoom");
    const createRoomButton = document.querySelector(".create-room");
    const roomCodeInput = document.getElementById("roomCode");
    const joinRoomForm = document.querySelector("form");
    const socket = io();

    let currentRoom = "General";
    let privateRooms = new Set();

    function scrollMessagesToBottom(room) {
        const messagesContainer = document.querySelector(`#${room} .messages`);
        if (messagesContainer) {
            setTimeout(() => {
                const messagesContainer = document.querySelector(`#${currentRoom}`);
                if (messagesContainer) {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
            }, 10);
        }
    }

    function switchRoom(room) {
        const allTabContents = document.querySelectorAll(".tabcontent");
    
        allTabContents.forEach((content) => {
            content.classList.remove("active");
            content.style.display = "none";
        });
    
        const activeTab = document.querySelector(`.tablinks.active`);
        if (activeTab) activeTab.classList.remove("active");
    
        currentRoom = room;
    
        const activeContent = document.getElementById(currentRoom);
        if (activeContent) {
            activeContent.classList.add("active");
            activeContent.style.display = "block";
        }

        const newActiveTab = document.querySelector(`.tablinks[data-tab="${currentRoom}"]`);
        if (newActiveTab) newActiveTab.classList.add("active");
    
        socket.emit("join_room", { room: currentRoom });
        console.log('switch room')
    }

    function removeRoomTab(roomCode) {
        const tab = document.querySelector(`.tablinks[data-tab="${roomCode}"]`);
        if (tab) {
            tab.remove();
        }

        const contentDiv = document.getElementById(roomCode);
        if (contentDiv) {
            contentDiv.remove();
        }

        privateRooms.delete(roomCode);
    }

    createRoomButton.addEventListener("click", async () => {
        if (privateRooms.size >= 5) {
            showModal("You can only join up to 5 private rooms.", "error");
            return;
        }

        try {
            const response = await fetch("/create_room", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });

            if (!response.ok) {
                showModal("Failed to create room.", "error");
                return;
            }

            const { room_code } = await response.json();
            showModal(`Room created! Code: ${room_code}`, "success");
            addNewRoomTab(room_code);
            privateRooms.add(room_code);
        } catch (error) {
            console.error("Error creating room:", error);
            showModal("Error creating room", "error");
        }
    });

    joinRoomForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const roomCode = roomCodeInput.value.trim();

        if (!roomCode) {
            showModal("Please enter a room code", "error");
            return;
        }
        if (privateRooms.has(roomCode)) {
            showModal("You have already joined this private room.", "error");
            return;
        }

        try {
            const response = await fetch("/join_room", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ room_code: roomCode }),
            });

            if (!response.ok) {
                showModal("Room not found", "error");
                return;
            }

            showModal(`Joined room: ${roomCode}`, "success");
            addNewRoomTab(roomCode);
            privateRooms.add(roomCode);

            console.log('test join')
        } catch (error) {
            console.error("Error joining room:", error);
            showModal("Error joining room", "error");
        }
    });

    sendMessageButton.addEventListener("click", sendMessage);

    messageInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });

    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        socket.emit("send_message", { room: currentRoom, message });
        console.log({ room: currentRoom, message })
        messageInput.value = "";

        scrollMessagesToBottom(currentRoom);
    }

    leaveRoomButton.addEventListener("click", () => {
        if (currentRoom === "General" || currentRoom === "Deck" || currentRoom === "Events") {
            showModal("You cannot leave the default rooms: try a private room.", "info");
            return;
        }

        socket.emit("leave_room", { room: currentRoom });
        console.log('leave room')

        const messagesContainer = document.querySelector(`#${currentRoom} .messages`);
        if (messagesContainer) {
            messagesContainer.innerHTML = "";
        }

        showModal(`You have left the room: ${currentRoom}`, "success");

        if (privateRooms.has(currentRoom)) {
            removeRoomTab(currentRoom);
        }

        currentRoom = "General";
        switchRoom(currentRoom);
    });

    function addNewRoomTab(roomCode) {
        const existingTab = document.querySelector(`.tablinks[data-tab="${roomCode}"]`);
        if (existingTab) {
            existingTab.click();
            return;
        }

        const newTab = document.createElement("button");
        newTab.classList.add("tablinks");
        newTab.dataset.tab = roomCode;
        newTab.textContent = roomCode;
        newTab.setAttribute("type", "button");
        document.querySelector(".tabs").appendChild(newTab);

        newTab.addEventListener("click", () => {
            switchRoom(roomCode);
        });

        const newTabContent = document.createElement("div");
        newTabContent.id = roomCode;
        newTabContent.classList.add("tabcontent");
        newTabContent.style.display = "none";

        newTabContent.innerHTML = `
            <h3>${roomCode}</h3>
            <div class="messages"></div>
            <button class="leave-private-room">Leave This Private Room</button>
        `;

        const leavePrivateRoomButton = newTabContent.querySelector(".leave-private-room");
        leavePrivateRoomButton.addEventListener("click", () => {
            switchRoom(roomCode);
            leaveRoomButton.click();
        });

        document.querySelector(".chat-rooms-container").appendChild(newTabContent);
        switchRoom(roomCode);
    }

    socket.on("receive_message", ({ room, message, username }) => {
        const messagesContainer = document.querySelector(`#${room} .messages`);
        if (messagesContainer) {
            const messageElement = document.createElement("div");
            messageElement.classList.add("message");
            messageElement.textContent = `${username}: ${message}`;
            messagesContainer.appendChild(messageElement);

            scrollMessagesToBottom(room);
        } else {
            console.error(`Messages container for room ${room} not found.`);
        }
    });

    socket.on("room_history", (history) => {
        const messagesContainer = document.querySelector(`#${currentRoom} .messages`);
        if (!messagesContainer) return;

        messagesContainer.innerHTML = "";
        history.forEach((msgObj) => {
            const messageElement = document.createElement("div");
            messageElement.classList.add("message");
            messageElement.textContent = `${msgObj.username}: ${msgObj.message}`;
            messagesContainer.appendChild(messageElement);
        });

        scrollMessagesToBottom(currentRoom);
    });

    socket.on("chat_error", (data) => {
        showModal(data.message, "error");
    });

    socket.emit("join_room", { room: "General" });
});
