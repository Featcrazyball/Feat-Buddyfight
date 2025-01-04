document.querySelectorAll('.shop-item').forEach(item => {
    item.addEventListener('click', function () {
        const itemId = this.getAttribute('data-item-id');
        const itemPrice = this.getAttribute('data-item-price');

        document.getElementById('modal-item-id').value = itemId;
        document.getElementById('modal-item-price').value = itemPrice;
        document.getElementById('modal-item-price-display').textContent = parseFloat(itemPrice).toFixed(2);

        document.getElementById('paymentModal').style.display = 'block';
    });
});

document.querySelector('.close').addEventListener('click', function () {
    document.getElementById('paymentModal').style.display = 'none';
});

window.addEventListener('click', function (e) {
    if (e.target == document.getElementById('paymentModal')) {
        document.getElementById('paymentModal').style.display = 'none';
    }
});

document.getElementById('paymentForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const formData = new FormData(this);

    try {
        const response = await fetch('/shops/make_payment', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            showModal(data.message, 'success');
            document.getElementById('paymentModal').style.display = 'none';
        } else {
            showModal(data.message, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showModal('An unexpected error occurred. Please try again.', 'error');
    }
});
