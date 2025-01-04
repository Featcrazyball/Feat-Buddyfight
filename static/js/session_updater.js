function updateSessionAndGoBack() {
    fetch('/update_session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.href = document.referrer || '/defaultFallbackPage';
            } else {
                console.error('Failed to update session:', data.message);
            }
        })
        .catch(error => {
            console.error('Error updating session:', error);
        });
}
