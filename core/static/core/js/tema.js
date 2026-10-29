(() => {
  const oscuro = window.matchMedia('(prefers-color-scheme: dark)');
  const aplicar = () => document.documentElement.setAttribute('data-bs-theme', oscuro.matches ? 'dark' : 'light');
  aplicar();
  oscuro.addEventListener('change', aplicar);
})();
