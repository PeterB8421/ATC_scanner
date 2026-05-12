/*
Author: Bc. Petr Balok
 */
document.addEventListener("DOMContentLoaded", function() {
    // Get the current URL path
    const currentPath = window.location.pathname;

    // Get all the nav links
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

    navLinks.forEach(link => {
        // If the link's href matches the current browser path
        if (link.getAttribute('href') === currentPath) {
            // Add the Bootstrap active class
            link.classList.add('active', 'fw-bold');
            link.setAttribute('aria-current', 'page');
        }
    });
});
