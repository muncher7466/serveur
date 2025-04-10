// Fonction pour initialiser les tooltips Bootstrap
function initTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
}

// Fonction pour initialiser les popovers Bootstrap
function initPopovers() {
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
}

// Fonction pour confirmer la suppression
function confirmDelete(event, message) {
    if (!confirm(message || 'Êtes-vous sûr de vouloir supprimer cet élément ?')) {
        event.preventDefault();
        return false;
    }
    return true;
}

// Fonction pour filtrer les tableaux
function filterTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    const filter = input.value.toUpperCase();
    const table = document.getElementById(tableId);
    const tr = table.getElementsByTagName("tr");

    for (let i = 1; i < tr.length; i++) {
        let found = false;
        const td = tr[i].getElementsByTagName("td");
        
        for (let j = 0; j < td.length; j++) {
            if (td[j]) {
                const txtValue = td[j].textContent || td[j].innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    found = true;
                    break;
                }
            }
        }
        
        tr[i].style.display = found ? "" : "none";
    }
}

// Fonction pour ajuster la quantité de stock
function ajusterStock(pieceId, url) {
    const quantite = prompt("Entrez la nouvelle quantité :");
    
    if (quantite !== null && !isNaN(quantite) && quantite >= 0) {
        const formData = new FormData();
        formData.append('quantite', quantite);
        
        fetch(url, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Mettre à jour l'affichage sans recharger la page
                document.getElementById(`quantite-${pieceId}`).textContent = quantite;
                // Afficher un message de succès
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-success alert-dismissible fade show';
                alertDiv.innerHTML = `
                    ${data.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
                
                // Supprimer l'alerte après 3 secondes
                setTimeout(() => {
                    alertDiv.remove();
                }, 3000);
            } else {
                alert(data.message || 'Une erreur est survenue');
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Une erreur est survenue lors de l\'ajustement du stock');
        });
    }
}

// Fonction pour calculer le coût total d'une intervention
function calculerCoutTotal() {
    let coutPieces = 0;
    const piecesInputs = document.querySelectorAll('[id^="piece_"]');
    
    piecesInputs.forEach(input => {
        if (input.value && !isNaN(input.value) && input.value > 0) {
            const pieceId = input.id.replace('piece_', '');
            const prixUnitaire = parseFloat(document.getElementById(`prix_${pieceId}`).value);
            coutPieces += input.value * prixUnitaire;
        }
    });
    
    const coutMainOeuvre = parseFloat(document.getElementById('cout_main_oeuvre').value) || 0;
    const coutTotal = coutPieces + coutMainOeuvre;
    
    document.getElementById('cout_pieces').textContent = coutPieces.toFixed(2) + ' €';
    document.getElementById('cout_total').textContent = coutTotal.toFixed(2) + ' €';
}

// Fonction pour mettre à jour le compteur de messages non lus
function updateUnreadCount() {
    fetch('/api/unread-count')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('unread-badge');
            if (badge) {
                badge.textContent = data.count;
                badge.style.display = data.count > 0 ? 'inline-block' : 'none';
            }
        })
        .catch(error => console.error('Erreur:', error));
}

// Fonction pour marquer un message comme lu
function markMessageAsRead(messageId) {
    fetch(`/messages/marquer_lu/${messageId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateUnreadCount();
        }
    })
    .catch(error => console.error('Erreur:', error));
}

// Fonction pour charger les messages d'une conversation
function loadConversationMessages(conversationId) {
    fetch(`/api/messages/${conversationId}`)
        .then(response => response.json())
        .then(messages => {
            const messageContainer = document.getElementById('messages-container');
            if (messageContainer) {
                messageContainer.innerHTML = '';
                messages.forEach(message => {
                    const messageElement = createMessageElement(message);
                    messageContainer.appendChild(messageElement);
                    if (!message.lu || !message.lu[currentUserId]) {
                        markMessageAsRead(message.id);
                    }
                });
                messageContainer.scrollTop = messageContainer.scrollHeight;
            }
        })
        .catch(error => console.error('Erreur:', error));
}

// Fonction pour créer un élément de message
function createMessageElement(message) {
    const div = document.createElement('div');
    div.className = `message ${message.sender_id === currentUserId ? 'sent' : 'received'}`;
    div.innerHTML = `
        <div class="message-content">
            <small class="sender">${message.sender_name}</small>
            <p>${message.content}</p>
            <small class="time">${new Date(message.created_at).toLocaleString()}</small>
        </div>
    `;
    return div;
}

// Fonction pour initialiser les notifications
function initNotifications() {
    // Vérifier les messages non lus toutes les 30 secondes
    function checkUnreadMessages() {
        fetch('/api/unread-count')
            .then(response => response.json())
            .then(data => {
                const badge = document.getElementById('unread-badge');
                if (badge) {
                    if (data.count > 0) {
                        badge.textContent = data.count;
                        badge.style.display = 'inline-block';
                    } else {
                        badge.style.display = 'none';
                    }
                }
            })
            .catch(error => console.error('Erreur:', error));
    }

    // Vérifier immédiatement et toutes les 30 secondes
    checkUnreadMessages();
    setInterval(checkUnreadMessages, 30000);
}

// Initialisation lorsque le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les composants Bootstrap
    initTooltips();
    initPopovers();
    
    // Initialiser les notifications
    initNotifications();
    
    // Ajouter des écouteurs d'événements pour les boutons de suppression
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            confirmDelete(event, this.getAttribute('data-confirm-message'));
        });
    });
    
    // Ajouter des écouteurs d'événements pour les champs de recherche
    const searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(input => {
        input.addEventListener('keyup', function() {
            filterTable(this.id, this.getAttribute('data-table'));
        });
    });
    
    // Ajouter des écouteurs d'événements pour le calcul du coût total
    const piecesInputs = document.querySelectorAll('[id^="piece_"]');
    const coutMainOeuvreInput = document.getElementById('cout_main_oeuvre');
    
    if (piecesInputs.length > 0 && coutMainOeuvreInput) {
        piecesInputs.forEach(input => {
            input.addEventListener('change', calculerCoutTotal);
        });
        
        coutMainOeuvreInput.addEventListener('change', calculerCoutTotal);
        
        // Calculer le coût initial
        calculerCoutTotal();
    }
    
    // Charger les messages si on est dans une conversation
    const conversationContainer = document.getElementById('messages-container');
    if (conversationContainer) {
        const conversationId = conversationContainer.getAttribute('data-conversation-id');
        if (conversationId) {
            loadConversationMessages(conversationId);
            // Actualiser les messages toutes les 10 secondes
            setInterval(() => loadConversationMessages(conversationId), 10000);
        }
    }
});
