// Ana JavaScript dosyası

document.addEventListener('DOMContentLoaded', function() {
    // Flash mesajlarının otomatik olarak kapanması
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            const closeButton = message.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });

    // Formları doğrulama
    const forms = document.querySelectorAll('form:not(#impressumForm)');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // İletişim formunu işleme
    const contactForm = document.querySelector('form#contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', function(event) {
            event.preventDefault();
            // Normalde burada bir AJAX isteği olurdu, ancak bu demo için sadece bir mesaj gösterelim
            const formData = new FormData(contactForm);
            let message = '';
            
            for (let [key, value] of formData.entries()) {
                message += `${key}: ${value}\n`;
            }
            
            alert('Teşekkürler! Mesajınız gönderildi. Kısa süre içinde size dönüş yapacağız.');
            contactForm.reset();
        });
    }

    // Abone ol formu
    const subscribeForm = document.querySelector('form#subscribeForm');
    if (subscribeForm) {
        subscribeForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const email = subscribeForm.querySelector('input[type="email"]').value;
            
            if (email) {
                alert(`${email} adresiniz bültenimize başarıyla kaydedildi. Teşekkürler!`);
                subscribeForm.reset();
            }
        });
    }

    // Künye düzenleyici için zengin metin editörü
    const impressumEditor = document.getElementById('impressumEditor');
    if (impressumEditor) {
        // Burada basit bir HTML düzenleyici ekleyebilirsiniz
        // Bu bir demo için basit tutulmuştur
    }
});

// Resimler yüklendiğinde boyutları ayarlama
window.addEventListener('load', function() {
    const images = document.querySelectorAll('img');
    images.forEach(function(img) {
        img.addEventListener('error', function() {
            this.src = '/static/img/error-image.png';
        });
    });
}); 