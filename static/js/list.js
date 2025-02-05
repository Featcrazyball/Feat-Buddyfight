function toggleFilter() {
    var filterPanel = document.getElementById('filter-panel');
    if (filterPanel.style.display === 'none' || filterPanel.style.display === '') {
        filterPanel.style.display = 'block';
    } else {
        filterPanel.style.display = 'none';
    }
}

function resetFilter() {
    document.getElementById('type').value = '';
    document.getElementById('rarity').value = '';
    document.getElementById('world').value = '';
    document.getElementById('size').value = '';
    document.getElementById('attribute').value = '';
    document.getElementById('unlocked').checked = false;
}

function openModal(cardId) {
    const card = cardsData.find(c => c.id === cardId);

    if (card) {
        document.getElementById('modal-title').innerText = card.name;
        document.getElementById('modal-card-no').innerText = card.card_no;
        document.getElementById('modal-rarity').innerText = card.rarity;
        document.getElementById('modal-attribute').innerText = card.attribute;
        document.getElementById('modal-world').innerText = card.world;
        document.getElementById('modal-size').innerText = card.size;
        document.getElementById('modal-power').innerText = card.power;
        document.getElementById('modal-defense').innerText = card.defense;
        document.getElementById('modal-type').innerText = card.type;

        const abilityParts = card.ability_effect.split('■');
        const mainParts = abilityParts.shift();
        const restParts = abilityParts.join('<br>■');

        // Handle ・ in the main text
        const dotParts = mainParts.split('・');
        const formattedMain = dotParts.join('<br>・');

        // Combine everything
        document.getElementById('modal-ability').innerHTML = formatAbilityText(card.ability_effect);

        document.getElementById('modal-image').src = card.image_url;
        document.getElementById('modal-image').alt = card.name;

        const updateBtn = document.getElementById('modal-update-btn');
        const deleteForm = document.getElementById('delete-card-form');

        if (updateBtn) {
            updateBtn.href = `/update_card/${card.id}`;
        }

        if (deleteForm) {
            deleteForm.action = `/delete_card/${card.id}`;
        }

        document.getElementById('card-modal').style.display = 'flex';

        document.addEventListener('keydown', handleKeyDown);
    } else {
        console.error('Card not found for ID:', cardId);
    }
}

function closeModal() {
    const modal = document.getElementById('card-modal');
    modal.style.display = 'none';

    document.removeEventListener('keydown', handleKeyDown);
}

window.onclick = function (event) {
    const modal = document.getElementById('card-modal');
    if (event.target === modal) {
        closeModal();
    }
};

function handleKeyDown(event) {
    if (event.key === 'Escape') {
        closeModal();
    }
}