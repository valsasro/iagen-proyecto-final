# Proyecto final: Brújula, asistente para campamentos juveniles

**Autor: Roberto Val**

## El problema

Organizar una actividad juvenil de tiempo libre en Castilla y León implica localizar y cruzar normativa, instrucciones, formularios y datos de lugares publicados en varias páginas. Hoy una persona organizadora debe buscarlos manualmente, identificar qué requisito corresponde a su actividad y volver a la fuente oficial para comprobarlo; esto consume tiempo y aumenta el riesgo de pasar por alto un trámite o aplicar una instrucción fuera de contexto.

No se midió cuánto tiempo ahorra la aplicación ni la frecuencia de estos errores. Esas cifras deben obtenerse observando el proceso real de las personas organizadoras.

## Herramienta principal

**Extracción de datos y RAG** (generación aumentada por recuperación), implementados como una aplicación web propia. El preparador recopila contenido público; el servidor recupera fragmentos pertinentes mediante embeddings y genera respuestas con referencias. La interfaz permite conversar y explorar la biblioteca documental.

## La solución

El servidor está en [servidor.py](servidor.py) y prepara los datos [preparar_datos.py](preparar_datos.py). La interfaz está en [web/](web/). Este es el control principal que evita pedir una respuesta generada cuando la recuperación documental no alcanza el umbral configurado:

```python
if similitud_maxima is None or similitud_maxima < SIMILARITY_THRESHOLD:
    return respuesta_no_consta(similitud_maxima)

if es_consulta_estadistica_sin_serie(pregunta, motor.documentos):
    return respuesta_no_consta(similitud_maxima)
```

El índice vectorial se conserva en disco para no recalcular todos los embeddings en cada arranque. El navegador solo usa las rutas de la API; la clave de OpenAI se carga en Python desde `.env`.

**Ejemplo de consulta y resultado real:**

```text
Pregunta: ¿Cuánto tiempo tengo para registrar la actividad de tiempo libre en JCYL,
porque mi campamento comienza dentro de 2 semanas?

Respuesta: Para un campamento, la comunicación debe presentarse antes de que empiece
y con al menos 7 días naturales de antelación. Dos semanas serían suficientes si,
al presentar la comunicación, quedan 7 días o más.

Fuentes mostradas: DOC-002, Orden FAM/203/2016; DOC-004, Orden FAM/688/2021.
```

Cuando la aplicación no encuentra información, responde «No consta en los documentos disponibles» y no ofrece una cifra o previsión inventada. Por ejemplo, la consulta sobre el tiempo de mañana en Valladolid queda sin responder porque el corpus no incluye datos meteorológicos.

**Archivos de la entrega:** [informe HTML](entregable.html), [informe PDF](entregable.pdf), [capturas de la aplicación](capturas/) y [resultados registrados](capturas/verificacion.json). No hay un enlace a un repositorio remoto publicado; la entrega es este proyecto.

### Arranque local

Requisitos: Python 3.12, `uv`, Node.js, npm y una clave de API de OpenAI.

1. Guarda `OPENAI_API_KEY` en `.env` en la raíz del proyecto. Si tu red lo requiere, configura también `HTTPS_PROXY` y `HTTP_PROXY`. No compartas ese archivo.
2. Instala dependencias y prepara el corpus:

   ```powershell
   uv sync
   uv run preparar_datos.py
   ```

3. En un terminal, inicia el servidor:

   ```powershell
   uv run servidor.py
   ```

   La API escucha en `http://127.0.0.1:8000`.

4. En otro terminal, instala y arranca la interfaz:

   ```powershell
   cd web
   npm install
   npm run dev
   ```

   Abre la dirección que muestre Vite, normalmente `http://localhost:5173`. El proxy de desarrollo reenvía `/api` al servidor Python.

La API ofrece `POST /api/preguntar` (pregunta, historial, respuesta estructurada y fuentes) y `GET /api/documentos` (listado filtrable). La documentación interactiva está en `http://127.0.0.1:8000/docs`.

## Cómo lo verificaste

- **Fuentes revisadas:** [Ley 11/2002, artículo 37.3, texto del BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2002-15544&p=20210929&tn=1), sobre evaluación de riesgos; [Orden FAM/688/2021, BOCYL](https://bocyl.jcyl.es/eli/es-cl/o/2021/05/21/fam688/), que modifica la Orden FAM/203/2016 y el plazo de comunicación; y el registro DOC-021 de ratios de responsables, enlazado en la [captura de la consulta de monitores](capturas/08-monitores.png). La respuesta sobre evaluación de riesgos no encontró la fuente de la Ley, aunque esa fuente está en el corpus.
- **Cifras, fechas y nombres comprobados:** el artículo 3 de la Orden FAM/203/2016, en la redacción modificada, establece al menos siete días naturales para actividades al aire libre y cuatro para otras actividades con riesgo moderado o importante. El documento DOC-021 indica un monitor por cada grupo de hasta 10 participantes en actividades de riesgo moderado o importante; la respuesta calculó cuatro para 38 participantes. La aplicación no tiene pronóstico meteorológico ni recuento anual agregado de campamentos.
- **Casos revisados:** se guardaron nueve preguntas en `capturas/verificacion.json` (las cuatro originales y las cinco añadidas). No se asigna una puntuación global de aciertos. Se identificó una omisión concreta: «¿Es obligatoria siempre hacer la evaluación de riesgos?» obtuvo «No consta», pese a que el artículo 37.3 de la Ley 11/2002 recoge la obligación para las actividades sujetas a esa ley. El informe [entregable.html](entregable.html) documenta esta limitación.
- **Cuando no sabe:** el servidor devuelve «No consta en los documentos disponibles» si la similitud de recuperación es menor que el umbral o si se pregunta por una estadística que no existe en el corpus. No envía esos casos al modelo para que invente una respuesta.
- **Código y comandos:** se revisaron el servidor, el preparador de datos y la interfaz. Se ejecutó el flujo de capturas con Microsoft Edge y se generó el PDF A4; se comprobó que tiene 17 páginas. No se ejecutaron comandos destructivos. La construcción de producción de Vite no forma parte de esta comprobación.

## Datos

- [x] Se usan documentos y contenido públicos de [Organización y gestión de campamentos de Juventud JCyL](https://juventud.jcyl.es/web/es/actividades-tiempo-libre/organizacion-gestion-campamentos.html), [Ayuda WIRI](https://servicios.jcyl.es/wiri/?inicio=ayuda) y el directorio público de lugares de Juventud. No se han añadido datos personales privados.
- [x] La clave de API no está en el código fuente. `.env` aparece en `.gitignore` y no está entre los archivos rastreados por Git; la aplicación la carga en el servidor, no en el navegador.

El corpus y el índice son locales y pueden actualizarse al volver a ejecutar `uv run preparar_datos.py`. La disponibilidad de los documentos y la vigencia de sus contenidos dependen de las fuentes oficiales.

## Qué falta para usarlo de verdad

- Corregir y volver a revisar la recuperación de preguntas jurídicas como la obligación de evaluar riesgos; no debería responder «No consta» cuando el corpus contiene la norma aplicable.
- Pedir a personal competente que revise las respuestas, las ratios y la interpretación de la normativa vigente antes de usar la herramienta para tramitar una actividad real.
- Definir una rutina de actualización del corpus y comprobar los cambios de las páginas y documentos oficiales.
- Conectar, si se necesita responderlas, fuentes autorizadas y actualizadas para previsión meteorológica y estadísticas anuales. Actualmente esas preguntas deben quedar sin respuesta.
- Medir con organizadores el tiempo ahorrado, la calidad de las respuestas y los casos en que las fuentes no bastan.
- Antes de publicar el servicio, configurar de forma segura la clave de API, el alojamiento, los límites de uso, la monitorización y la política de conservación de consultas.
