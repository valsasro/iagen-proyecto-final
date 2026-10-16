# Brújula · Asistente para campamentos juveniles

**Autor: Roberto Val**

Brújula es una aplicación web para resolver dudas sobre la organización y gestión de actividades juveniles de tiempo libre en Castilla y León. Responde a partir de documentos y registros públicos, muestra los fragmentos que respaldan cada respuesta y avisa cuando la información no consta en la biblioteca consultada.

## Qué incluye

- Chat para consultar consejos, trámites, evaluación de riesgos, ratios de responsables y lugares para las actividades.
- Referencias bajo cada respuesta, con enlace, título y fragmento del documento utilizado.
- Respuesta «No consta» cuando no se encuentra respaldo suficiente; el asistente no debe completar esos datos con información inventada.
- Biblioteca de documentos con búsqueda por texto y filtro por tipo.
- API en Python con FastAPI y una interfaz en Svelte, TypeScript y Vite.
- Recuperación aumentada por búsqueda (RAG): embeddings `text-embedding-3-small`, índice local persistido y respuestas generadas con `gpt-6-luna`.
- Informe del proyecto y capturas en `entregable.html`, `entregable.pdf` y `capturas/`.

## Fuentes de datos

El preparador de datos recoge documentos PDF y contenido público desde:

- [Organización y gestión de campamentos · Juventud Castilla y León](https://juventud.jcyl.es/web/es/actividades-tiempo-libre/organizacion-gestion-campamentos.html)
- [Ayuda WIRI](https://servicios.jcyl.es/wiri/?inicio=ayuda)
- El directorio público de instalaciones y lugares de Juventud que utiliza el proyecto.

Las respuestas son una ayuda de consulta. Conviene abrir las fuentes oficiales enlazadas para confirmar la normativa vigente y los requisitos de cada actividad.

## Requisitos

- Python 3.12 y [uv](https://docs.astral.sh/uv/).
- Node.js y npm.
- Una clave de API de OpenAI. El navegador no recibe esta clave.

## Configuración

1. Crea un archivo `.env` en la raíz del proyecto con la clave:

   ```dotenv
   OPENAI_API_KEY=tu_clave
   ```

   Si la red requiere proxy, añade también las variables `HTTPS_PROXY` y, si corresponde, `HTTP_PROXY`. No compartas ni publiques el archivo `.env`.

2. Instala las dependencias de Python y prepara el corpus:

   ```powershell
   uv sync
   uv run preparar_datos.py
   ```

   El preparador descarga y extrae el contenido público de las fuentes configuradas y lo guarda en `data/corpus.json`. El índice de embeddings se crea y persiste en `data/indice_embeddings.npz` cuando arranca el servidor por primera vez, y se reutiliza en los siguientes arranques mientras el corpus no cambie.

3. Instala las dependencias de la interfaz:

   ```powershell
   cd web
   npm install
   cd ..
   ```

## Arrancar la aplicación

Abre dos terminales desde la carpeta del proyecto.

En la primera, inicia la API:

```powershell
uv run servidor.py
```

La API queda disponible en `http://127.0.0.1:8000`.

En la segunda, inicia la interfaz:

```powershell
cd web
npm run dev
```

Abre la dirección que muestre Vite, normalmente `http://localhost:5173`. Vite reenvía las peticiones `/api` al servidor Python del puerto 8000.

## API

- `POST /api/preguntar`: recibe `pregunta` y un `historial` opcional; devuelve la respuesta, las fuentes, el indicador `no_consta` y la similitud máxima.
- `GET /api/documentos`: lista documentos. Admite `q`, `tipo`, `offset` y `limite` como parámetros de búsqueda y paginación.

La documentación interactiva de FastAPI está en `http://127.0.0.1:8000/docs`.

## Construir la interfaz

Desde `web/`:

```powershell
npm run build
```

