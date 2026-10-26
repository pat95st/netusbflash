// Follow the operating system's light/dark preference (loaded in <head> to avoid a flash).
(function () {
    var media = window.matchMedia('(prefers-color-scheme: dark)');
    function apply() {
        document.documentElement.setAttribute('data-bs-theme', media.matches ? 'dark' : 'light');
    }
    apply();
    if (media.addEventListener) {
        media.addEventListener('change', apply);
    }
})();
