document.querySelectorAll('input[type="password"]').forEach((campo) => {
  const grupo = document.createElement('div');
  grupo.className = 'input-group';
  campo.parentNode.insertBefore(grupo, campo);
  grupo.appendChild(campo);

  const boton = document.createElement('button');
  boton.type = 'button';
  boton.className = 'btn btn-outline-secondary';
  boton.setAttribute('aria-label', 'Mostrar contraseña');
  boton.setAttribute('aria-pressed', 'false');
  boton.innerHTML = '<i class="bx bx-show" aria-hidden="true"></i>';
  boton.addEventListener('click', () => {
    const visible = campo.type === 'password';
    campo.type = visible ? 'text' : 'password';
    boton.setAttribute('aria-pressed', String(visible));
    boton.setAttribute('aria-label', visible ? 'Ocultar contraseña' : 'Mostrar contraseña');
    boton.firstElementChild.className = visible ? 'bx bx-hide' : 'bx bx-show';
  });
  grupo.appendChild(boton);
});
