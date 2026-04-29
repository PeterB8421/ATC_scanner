/*
Author: Bc. Petr Balok
 */
document.addEventListener("DOMContentLoaded", function() {
    // 1. Get the current URL path (e.g., "/settings/")
    const currentPath = window.location.pathname;

    // 2. Find all the nav links
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

    // 3. Loop through them and compare
    navLinks.forEach(link => {
        // If the link's href matches the current browser path
        if (link.getAttribute('href') === currentPath) {
            // Add the Bootstrap active class
            link.classList.add('active', 'fw-bold');

            // Good for screen readers!
            link.setAttribute('aria-current', 'page');
        }
    });
});
