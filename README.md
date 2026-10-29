# Gestión de novedades

Registro de novedades académicas, disciplinarias y de ambiente, con evidencia adjunta.
Requiere Python 3.12 o superior.

## Puesta en marcha

    python -m venv .venv
    source .venv/bin/activate        # en Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env             # en Windows: copy .env.example .env
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

Con MySQL: `pip install -r requirements-mysql.txt` y completa `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
Sin `DB_NAME` se usa SQLite.

## Datos de ejemplo

    python manage.py cargar_demo             # usuarios demo_*, clave: Demo-Novedades-2026
    python manage.py cargar_demo --limpiar   # borra lo demo y lo regenera

Incluye el superusuario `demo_admin`. Solo funciona con los settings de desarrollo.

## Estructura

    config/        settings por entorno (base, desarrollo, produccion), urls y router de la API
    core/          utilidades compartidas: archivos, formularios, plantillas base, comando de demo
    catalogo/      sedes, programas, fichas y ambientes
    cuentas/       usuarios, login, registro, perfil con foto, bloqueos de acceso
    novedades/     novedades, permisos por rol, tabla, evidencias

Cada app tiene sus propios modelos, vistas, formularios, serializadores, API, admin, plantillas y pruebas.
Una app nueva se crea igual, se agrega a `INSTALLED_APPS` y registra su viewset en `config/api.py`.
Las dependencias van en una sola dirección: `catalogo` ← `cuentas` ← `novedades`, y todas pueden usar `core`.

## Entornos

`manage.py` usa `config.settings.desarrollo`; `wsgi.py` y `asgi.py` usan `config.settings.produccion`.
Para correr comandos en producción: `DJANGO_SETTINGS_MODULE=config.settings.produccion python manage.py ...`.
En producción hay HTTPS obligatorio, cookies seguras y HSTS, y se exige `DJANGO_SECRET_KEY`
(genera una con `python -c "import secrets; print(secrets.token_urlsafe(60))"`).
Si va detrás de un proxy que termina TLS, pon `DJANGO_PROXY_SSL=1`.
Ejecuta `collectstatic` y sirve `estaticos/` desde el servidor web. Nunca sirvas `privado/` (evidencias y fotos).

## Pruebas

    python manage.py test

## Roles

| Rol | Ve | Puede |
|---|---|---|
| Aprendiz | Sus novedades | Consultar y descargar su evidencia |
| Instructor | Las que registró | Crear, editar y eliminar las suyas |
| Coordinador | Las de aprendices de su sede | Crear, editar y eliminar dentro de su sede |
| Superusuario | Todo | Todo, más la administración en `/admin/` |

Quien se registra en `/cuentas/registro/` queda siempre como aprendiz. Los demás roles los asigna
el administrador. Sedes, programas, fichas, ambientes y usuarios se gestionan en `/admin/` o por la API.

## Archivos

Evidencias (PDF, PNG, JPG, hasta 5 MB) y fotos de perfil (hasta 3 MB, se recortan a 320x320 JPEG) se
guardan en `privado/` con nombre aleatorio y se entregan solo por vistas con control de permisos.
La descarga de una evidencia se llama `novedad-<tipo de documento><número>.<ext>`,
por ejemplo `novedad-CC1010148440.pdf`.

## Desbloquear usuarios

Tras 5 intentos fallidos el acceso se bloquea 15 minutos (por usuario e IP). Para levantar el bloqueo
antes: `/admin/` → Cuentas → Usuarios bloqueados, marca los registros y elige
"Desbloquear los usuarios seleccionados". Queda registrado en el historial del administrador.

## API

Autenticada con la misma sesión. Rutas bajo `/api/`: `sedes`, `programas`, `fichas`, `ambientes`,
`usuarios` (solo staff) y `novedades`. Las evidencias y fotos no tienen URL pública: `archivo_url` y
`foto_url` apuntan a la descarga con control de permisos.

## Librerías de interfaz

Bootstrap 5.3.8, Boxicons 2.1.4, DataTables 2.3.8 y jQuery 3.7.1 viajan dentro del proyecto
(`core/static/core/vendor/`), así que la aplicación no depende de ningún CDN.
