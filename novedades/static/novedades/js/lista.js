(() => {
  const elemento = document.getElementById('tabla-novedades');
  const filtro = document.getElementById('filtro-tipo');
  const indicadores = document.querySelectorAll('.indicador');

  const idioma = {
    emptyTable: 'Aún no hay novedades para mostrar',
    info: 'Mostrando _START_ a _END_ de _TOTAL_ novedades',
    infoEmpty: 'Sin resultados',
    infoFiltered: '(filtrado de _MAX_ en total)',
    lengthMenu: 'Mostrar _MENU_',
    loadingRecords: 'Cargando…',
    processing: 'Cargando…',
    search: 'Buscar:',
    searchPlaceholder: 'Aprendiz, documento o texto',
    zeroRecords: 'Ninguna novedad coincide con la búsqueda',
    paginate: { first: 'Primera', last: 'Última', next: 'Siguiente', previous: 'Anterior' },
  };

  const tabla = new DataTable(elemento, {
    serverSide: true,
    processing: true,
    searchDelay: 400,
    pageLength: 15,
    lengthMenu: [10, 15, 25, 50],
    order: [[0, 'desc']],
    ajax: {
      url: elemento.dataset.url,
      data: (peticion) => {
        peticion.tipo = filtro.value;
      },
    },
    columnDefs: [{ targets: [6, 7], orderable: false, searchable: false }],
    language: idioma,
  });

  const actualizar = () => {
    indicadores.forEach((indicador) => {
      const activo = indicador.dataset.tipo === filtro.value;
      indicador.classList.toggle('activo', activo);
      indicador.setAttribute('aria-pressed', String(activo));
    });
    tabla.ajax.reload();
  };

  filtro.addEventListener('change', actualizar);
  indicadores.forEach((indicador) => {
    indicador.addEventListener('click', () => {
      filtro.value = indicador.dataset.tipo;
      actualizar();
    });
  });
})();
