document.addEventListener('DOMContentLoaded', () => {
    const socket = io.connect('http://' + window.location.hostname + ':8000', { transports: ['websocket'] });

    const roomsContainer= document.getElementById('rooms-container');
    const waitingModal  = document.getElementById('waiting-modal');
    const roomCodeSpan  = document.getElementById('room-code');
    let currentRoomCode = null;

    socket.on('update_active_game_rooms', (gameRooms) => {
        console.log('Real-time active game rooms update received:', gameRooms);
        renderGameRooms(gameRooms);
    });

    socket.on('game_room_created', (data) => {
        if (data.status === 'success') {
            console.log('Successfully created room:', data.room_code);
            currentRoomCode = data.room_code;
            waitingModal.style.display = 'flex';
            sessionStorage.setItem('hasFetchedInitData', 'false');
            loadActiveGameRooms();
        } else {
            console.error('Error creating room:', data.message);
        }
    });

    socket.on('room_ready', (data) => {
        console.log('Room is ready event received:', data);
        if (data.room_code === currentRoomCode) {
            console.log(`My room ${data.room_code} is ready. Switching to gameplay...`);
            waitingModal.style.display = 'none';
            sessionStorage.setItem('hasFetchedInitData', 'false');
            window.location.href = data.redirect_url;
        }
    });

    socket.on('joining_game_player', (data) => {
        console.log('joining_game_player event:', data);
    });

    socket.on('room_creator_player', (data) => {
        console.log('room_creator_player event:', data);
    });

    socket.on('game_end', (data) => {
        console.log('Game end event:', data);
        showModal(data.message, 'success');
        currentRoomCode = null;
        loadActiveGameRooms();
    });

    socket.on('room_closed', (data) => {
        console.log('room_closed event:', data);
        showModal(data.message, 'error');
        waitingModal.style.display = 'none';
        currentRoomCode = null;
        loadActiveGameRooms();
    });

    socket.on('error', (data) => {
        console.error('Error event received:', data);
        const message = data.message || 'An unknown error occurred';
        showModal(message, 'error');
    });

    // Loading Rooms
    function loadActiveGameRooms() {
        fetch('/active_game_rooms', { method: 'GET', headers: { 'Content-Type': 'application/json' } })
            .then(response => response.json())
            .then(renderGameRooms)
            .catch(error => {
                console.error('Error loading game rooms:', error);
                renderGameRooms([]);
            });
    }

    function renderGameRooms(gameRooms) {
        roomsContainer.innerHTML = '';
        if (gameRooms.length === 0) {
            const noRoomsDiv = document.createElement('div');
            noRoomsDiv.className = 'lobby-rooms';
            noRoomsDiv.innerHTML = `<h1>No Rooms</h1>`;
            roomsContainer.appendChild(noRoomsDiv);
        }
        gameRooms.forEach(room => {
            const roomDiv = document.createElement('div');
            roomDiv.className = 'lobby-rooms';
            roomDiv.innerHTML = `
                <div class="user-information">
                    <div class="profile-picture" style="background-image: url('${room.creator_profile_picture}')"></div>
                    <div class="username">${room.creator_username}</div>
                </div>
                <div class="join" style="cursor: pointer;">
                    <p class="join-action">FIGHT</p>
                </div>`;
            roomsContainer.appendChild(roomDiv);
            roomDiv.querySelector('.join').addEventListener('click', () => {
                console.log(`Attempting to join room: ${room.room_code}`);
                socket.emit('join_game_room', { room: room.room_code });
                currentRoomCode = room.room_code; 
            });
        });
    }

    // Create Room
    document.querySelector('.create-room').addEventListener('click', () => {
        console.log('Create Room Button Clicked');
        socket.emit('create_game_room');
    });

    // Leave Room
    document.getElementById('leave-button').addEventListener('click', () => {
        if (currentRoomCode) {
            console.log('Leave Button Clicked');
            socket.emit('leave_created_game_room', { room: currentRoomCode });
            currentRoomCode = null;
            waitingModal.style.display = 'none';
        } else {
            console.error('No room to leave.');
        }
    });

    loadActiveGameRooms();
});
