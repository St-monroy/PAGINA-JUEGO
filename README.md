# SSRCM — guía sencilla

## Archivos principales

- `app.py`: servidor Python, rutas, cuentas y catálogo inicial de juegos.
- `templates/index.html`: página principal y catálogo.
- `templates/juego.html`: ficha de cada juego y reseñas.
- `templates/acceso.html`: registro e inicio de sesión.
- `templates/perfil.html`: perfil personalizable (nombre, avatar y biografía) y biblioteca.
- `templates/comunidad.html`: comunidad y publicaciones.
- `templates/panel.html`: panel de administración.
- `templates/base.html`: estructura compartida, menú y cabecera.
- `static/css/estilos.css`: colores, tamaños, diseño adaptable y estilos.
- `static/js/funciones.js`: slider, controles y pequeñas interacciones.
- `static/img/`: imágenes y portadas de los juegos.
- `instance/ssrcm.db`: base de datos local; se crea automáticamente.

## Cómo iniciar el proyecto en Windows

Abre CMD dentro de la carpeta donde está `app.py` y ejecuta: 

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador. Si ya creaste `.venv`, no repitas el primer comando; activa el entorno y continúa.

Si `pip install -r requirements.txt` dice que no encuentra el archivo, escribe `dir` y confirma que aparecen `app.py` y `requirements.txt` en esa misma carpeta.

## Cómo agregar un juego nuevo

### 1. Añade la portada

Copia una imagen JPG, PNG o WebP a `static/img/`. Usa un nombre sencillo, sin espacios, por ejemplo `mi-juego.jpg`.

### 2. Abre `app.py`

Busca la lista que comienza con `GAMES = [` cerca de la parte superior. Copia uno de los bloques de juego y pégalo dentro de esa lista, separado de los demás por una coma. Cambia sus datos. Ejemplo:

```python
{
    "id": "mi-juego",
    "name": "Mi Juego",
    "studio": "Mi Estudio",
    "category": "Aventura",
    "image": "mi-juego.jpg",
    "rating": 4.5,
    "downloads": "Demo",
    "size": "120 MB",
    "badge": "NUEVO",
    "description": "Escribe aquí una descripción breve del juego."
},
```

**Importante:** `id` debe ser único, en minúsculas y sin espacios. `image` debe coincidir exactamente con el nombre de la imagen. Las categorías disponibles inicialmente son `Aventura`, `RPG`, `Arcade`, `Simulación`, `Acción` y `Puzles`. Puedes dejar `badge` vacío (`"badge": ""`) si no quieres una etiqueta.

### 3. Guarda y reinicia

Guarda `app.py`. En la terminal detén el servidor con `Ctrl + C` y vuelve a ejecutar `python app.py`. Recarga la página.

### ¿Cómo hago para que el juego se pueda descargar o jugar?

Añadir una portada solo lo agrega al catálogo. Para ofrecer una descarga real, necesitarías un enlace legal al instalador o archivo del juego y agregar un campo de descarga al catálogo y a `templates/juego.html`. Para jugar dentro de la web, el juego debe ser compatible con navegador (por ejemplo, HTML5) y debe integrarse de forma segura. Esta versión no descarga ni instala juegos automáticamente.

## Personalizar el perfil

Después de iniciar sesión, abre **Mi perfil**. Puedes cambiar el nombre de usuario, elegir un avatar y escribir una biografía. Tus favoritos y reseñas se guardan en la base de datos local.

## Nota de seguridad

Esta configuración está pensada para pruebas en tu propio computador. Antes de publicar la web en Internet, configura una clave secreta permanente, protección CSRF para formularios, HTTPS y un servidor de producción. No uses el servidor de desarrollo de Flask como servidor público.
