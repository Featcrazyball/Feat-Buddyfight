document.addEventListener("DOMContentLoaded", () => {
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

    tabsContainer.addEventListener("click", (event) => {
        if (event.target.classList.contains("tablinks")) {
            switchRoom(event.target.dataset.tab);
        }
    });

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
            socket.emit("join_room", { room: room_code });
        } catch (error) {
            console.error("Error creating room:", error);
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
            socket.emit("join_room", { room: roomCode });
        } catch (error) {
            console.error("Error joining room:", error);
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

        console.log("Sending message:", { room: currentRoom, message });
        socket.emit("send_message", { room: currentRoom, message }); 
        messageInput.value = ""; 
    }

    socket.on("receive_message", ({ room, message, username }) => {
        console.log("Received message:", { room, message, username });
        const messagesContainer = document.querySelector(`#${room} .messages`);
        if (messagesContainer) {
            const messageElement = document.createElement("div");
            messageElement.classList.add("message");
            messageElement.textContent = `${username}: ${message}`;
            messagesContainer.appendChild(messageElement);
            messagesContainer.scrollTop = messagesContainer.scrollHeight; 
        } else {
            console.error(`Messages container for room ${room} not found.`);
        }
    });

    leaveRoomButton.addEventListener("click", () => {
        if (currentRoom !== "General") {
            socket.emit("leave_room", { room: currentRoom });
            const messagesContainer = document.querySelector(`#${currentRoom} .messages`);
            if (messagesContainer) {
                messagesContainer.innerHTML = "";
            }
            showModal("info", `You have left the room: ${currentRoom}`);
            privateRooms.delete(currentRoom);
            currentRoom = "General";
            socket.emit("join_room", { room: currentRoom });
            switchRoom(currentRoom);
        } else {
            showModal("info", "You are already in the General room.");
        }
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
        document.querySelector(".tabs").appendChild(newTab);

        const newTabContent = document.createElement("div");
        newTabContent.id = roomCode;
        newTabContent.classList.add("tabcontent");
        newTabContent.style.display = "none"; 

        newTabContent.innerHTML = `<h3>${roomCode}</h3><div class="messages"></div>`;

        if (privateRooms.has(roomCode)) {
            const leavePrivateRoomButton = document.createElement("button");
            leavePrivateRoomButton.textContent = "Leave Room";
            leavePrivateRoomButton.classList.add("leave-private-room");
            leavePrivateRoomButton.addEventListener("click", () => {
                leaveRoomButton.click(); 
            });
            newTabContent.appendChild(leavePrivateRoomButton);
        }

        document.querySelector(".chat-rooms-container").appendChild(newTabContent);

        switchRoom(roomCode);
    }

    socket.emit("join_room", { room: "General" });
});
