// Weight-based products functionality
document.addEventListener('DOMContentLoaded', function() {
    // Handle product selection change to show/hide weight input
    const productSelect = document.getElementById('productSelect');
    const productQuantity = document.getElementById('productQuantity');
    const productWeight = document.getElementById('productWeight');
    
    if (productSelect && productQuantity && productWeight) {
        productSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const isPerKg = selectedOption.getAttribute('data-per-kg') === 'true';
            
            if (isPerKg) {
                productQuantity.style.display = 'none';
                productWeight.style.display = 'block';
                productWeight.focus();
            } else {
                productWeight.style.display = 'none';
                productQuantity.style.display = 'block';
            }
        });
        
        // Validate weight input (minimum 0.5kg)
        productWeight.addEventListener('input', function() {
            const weight = parseFloat(this.value);
            if (weight && weight < 0.5) {
                this.value = 0.5;
                if (typeof showNotification === 'function') {
                    showNotification("Minimum weight is 0.5 kg", "warning");
                }
            } else if (weight > 50) {
                if (typeof showNotification === 'function') {
                    showNotification("Please verify this large weight amount: " + weight + " kg", "info");
                }
            }
        });
    }
    
    // Override the addProductBtn click handler to handle weight-based products
    const addProductBtn = document.getElementById('addProductBtn');
    if (addProductBtn) {
        // Remove existing event listeners and add our custom one
        const newBtn = addProductBtn.cloneNode(true);
        addProductBtn.parentNode.replaceChild(newBtn, addProductBtn);
        
        newBtn.addEventListener('click', function() {
            const productSelect = document.getElementById('productSelect');
            const productId = productSelect.value;
            
            if (!productId) {
                if (typeof showNotification === 'function') {
                    showNotification("Please select a product", "warning");
                }
                return;
            }
            
            const selectedOption = productSelect.options[productSelect.selectedIndex];
            const isPerKg = selectedOption.getAttribute('data-per-kg') === 'true';
            const productName = selectedOption.text.split(' - ')[0];
            const priceText = selectedOption.text.split('Rs.')[1];
            const productPrice = parseFloat(priceText ? priceText.split(' ')[0] : 0);
            
            let quantity;
            let displayText = '';
            
            if (isPerKg) {
                const weight = parseFloat(document.getElementById('productWeight').value) || 1;
                if (weight < 0.5) {
                    if (typeof showNotification === 'function') {
                        showNotification("Minimum weight is 0.5 kg", "warning");
                    }
                    return;
                }
                quantity = weight;
                displayText = weight + ' kg';
            } else {
                quantity = parseInt(document.getElementById('productQuantity').value) || 1;
                displayText = quantity + ' pcs';
            }
            
            // Call the original addItemToOrder function if available
            if (typeof addItemToOrder === 'function') {
                addItemToOrder(productId, productName, productPrice, quantity, false, isPerKg, displayText);
            } else {
                // Fallback: trigger the original button click
                triggerOriginalAddProduct(productId, quantity);
            }
            
            // Reset form
            productSelect.value = '';
            document.getElementById('productQuantity').value = 1;
            document.getElementById('productWeight').value = 1;
            document.getElementById('productWeight').style.display = 'none';
            document.getElementById('productQuantity').style.display = 'block';
        });
    }
    
    function triggerOriginalAddProduct(productId, quantity) {
        // Set the values in the form
        document.getElementById('productSelect').value = productId;
        document.getElementById('productQuantity').value = quantity;
        
        // Trigger a custom event or call jQuery if available
        if (typeof $ !== 'undefined' && typeof addItemToOrder === 'function') {
            const selectedOption = document.getElementById('productSelect').options[document.getElementById('productSelect').selectedIndex];
            const productName = selectedOption.text.split(' - ')[0];
            const priceText = selectedOption.text.split('Rs.')[1];
            const productPrice = parseFloat(priceText ? priceText.split(' ')[0] : 0);
            addItemToOrder(productId, productName, productPrice, quantity, false);
        }
    }
}); 