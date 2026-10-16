<script lang="ts">
  import { onMount, tick } from 'svelte'

  type Fuente = {
    id: string
    titulo: string
    url: string
    fragmento: string
    similitud: number
  }

  type Mensaje = {
    id: string
    role: 'user' | 'assistant'
    content: string
    fuentes?: Fuente[]
    no_consta?: boolean
    similitud_maxima?: number | null
    pending?: boolean
  }

  type Documento = {
    id: string
    titulo: string
    url: string
    tipo: string
    fecha_actualizacion: string | null
    cobertura: string
    caracteres: number
    fragmentos_indexados: number
  }

  type DocumentosResponse = {
    documentos: Documento[]
    total: number
    offset: number
    limite: number
  }

  const sugerencias = [
    '¿Qué consejos debo conocer para montar una actividad de tiempo libre, en concreto un campamento juvenil?',
    '¿Qué trámites administrativos debo hacer para la actividad de tiempo libre?',
    '¿Dónde puedo montar mi actividad de tiempo libre?',
  ]

  let pagina: 'chat' | 'documentos' = 'chat'
  let mensajes: Mensaje[] = []
  let pregunta = ''
  let enviando = false
  let cargandoDocs = false
  let errorDocs = ''
  let errorChat = ''
  let documentos: Documento[] = []
  let totalDocumentos = 0
  let consultaDocs = ''
  let tipoDoc = ''
  let conversacion: HTMLElement
  let temporizadorBusqueda: ReturnType<typeof setTimeout>

  $: fuentesIndexadas = documentos.reduce((suma, doc) => suma + doc.fragmentos_indexados, 0)

  onMount(() => {
    void cargarDocumentos()
  })

  async function cargarDocumentos() {
    cargandoDocs = true
    errorDocs = ''
    const parametros = new URLSearchParams({ limite: '100' })
    if (consultaDocs.trim()) parametros.set('q', consultaDocs.trim())
    if (tipoDoc) parametros.set('tipo', tipoDoc)

    try {
      const respuesta = await fetch(`/api/documentos?${parametros.toString()}`)
      if (!respuesta.ok) throw new Error(await mensajeError(respuesta))
      const datos = (await respuesta.json()) as DocumentosResponse
      documentos = datos.documentos
      totalDocumentos = datos.total
    } catch (error) {
      errorDocs = error instanceof Error ? error.message : 'No se pudo cargar la biblioteca.'
    } finally {
      cargandoDocs = false
    }
  }

  function buscarDocumentos() {
    clearTimeout(temporizadorBusqueda)
    temporizadorBusqueda = setTimeout(() => void cargarDocumentos(), 220)
  }

  async function mensajeError(respuesta: Response) {
    try {
      const datos = await respuesta.json()
      return datos.detail || `Error del servidor (${respuesta.status}).`
    } catch {
      return `Error del servidor (${respuesta.status}).`
    }
  }

  async function enviar(texto = pregunta) {
    const textoPregunta = texto.trim()
    if (!textoPregunta || enviando) return

    errorChat = ''
    const historial = mensajes
      .filter((mensaje) => mensaje.role !== 'assistant' || !mensaje.pending)
      .map(({ role, content }) => ({ role, content }))
    mensajes = [
      ...mensajes,
      { id: crypto.randomUUID(), role: 'user', content: textoPregunta },
      { id: crypto.randomUUID(), role: 'assistant', content: '', pending: true },
    ]
    pregunta = ''
    enviando = true
    await irAlFinal()

    try {
      const respuesta = await fetch('/api/preguntar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pregunta: textoPregunta, historial }),
      })
      if (!respuesta.ok) throw new Error(await mensajeError(respuesta))
      const datos = (await respuesta.json()) as Omit<Mensaje, 'id' | 'role' | 'pending'> & {
        respuesta: string
      }
      mensajes = mensajes.map((mensaje) =>
        mensaje.pending
          ? {
              id: mensaje.id,
              role: 'assistant',
              content: datos.respuesta,
              fuentes: datos.fuentes ?? [],
              no_consta: datos.no_consta ?? false,
              similitud_maxima: datos.similitud_maxima,
            }
          : mensaje,
      )
    } catch (error) {
      const detalle = error instanceof Error ? error.message : 'No se pudo consultar el asistente.'
      mensajes = mensajes.filter((mensaje) => !mensaje.pending)
      errorChat = `${detalle} Comprueba que el servidor Python está iniciado.`
    } finally {
      enviando = false
      await irAlFinal()
    }
  }

  async function irAlFinal() {
    await tick()
    if (conversacion) conversacion.scrollTop = conversacion.scrollHeight
  }

  function limpiarConversacion() {
    if (enviando) return
    mensajes = []
    errorChat = ''
  }

  function cambiarPagina(nueva: 'chat' | 'documentos') {
    pagina = nueva
    if (nueva === 'documentos') void cargarDocumentos()
  }

  function alEnviar(evento: SubmitEvent) {
    evento.preventDefault()
    void enviar()
  }

  function alEscribir(evento: KeyboardEvent) {
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault()
      void enviar()
    }
  }
</script>

<svelte:head>
  <title>Brújula · Campamentos juveniles</title>
  <meta
    name="description"
    content="Asistente con fuentes oficiales para organizar actividades juveniles de tiempo libre en Castilla y León."
  />
</svelte:head>

<div class="app-shell">
  <header class="site-header">
    <a class="brand" href="#inicio" onclick={(event) => { event.preventDefault(); cambiarPagina('chat') }}>
      <span class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none"><path d="m3 17 5.5-7 3.4 4 3.1-5L21 17H3Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M4 20h16" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><circle cx="18" cy="5" r="1.5" fill="currentColor"/></svg>
      </span>
      <span class="brand-copy"><strong>Brújula</strong><small>Campamentos juveniles</small></span>
    </a>
    <div class="header-meta">
      <span class="live-pill"><i></i> Fuentes oficiales</span>
      <span class="region-label">Castilla y León</span>
    </div>
  </header>

  <main class="page-wrap">
    <section class="welcome-row">
      <div>
        <p class="eyebrow">Organización y gestión · Tiempo libre</p>
        <h1>Resuelve dudas con las fuentes a mano.</h1>
        <p class="welcome-copy">Orientación para organizar actividades juveniles, revisar trámites y consultar documentos de referencia.</p>
      </div>
      <div class="welcome-note"><span class="note-icon">i</span><span>Contrasta cada obligación con la normativa vigente y las características de tu actividad.</span></div>
    </section>

    <div class="workspace">
      <aside class="sidebar" aria-label="Navegación de la aplicación">
        <p class="sidebar-label">ESPACIO DE TRABAJO</p>
        <button class:active={pagina === 'chat'} class="nav-item" onclick={() => cambiarPagina('chat')}>
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M3 4.5h14v9H9l-4.5 3v-3H3v-9Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6.5 8h7M6.5 10.5h4.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
          <span>Asistente</span>
          <span class="nav-mark">01</span>
        </button>
        <button class:active={pagina === 'documentos'} class="nav-item" onclick={() => cambiarPagina('documentos')}>
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M5 2.8h7l3 3v11.4H5V2.8Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 3v3h3M7.5 9h5M7.5 11.5h5M7.5 14h3" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/></svg>
          <span>Documentos</span>
          {#if totalDocumentos}<span class="nav-count">{totalDocumentos}</span>{/if}
        </button>

        <div class="sidebar-spacer"></div>
        <div class="sidebar-source-card">
          <span class="side-kicker">BIBLIOTECA CONECTADA</span>
          <strong>{totalDocumentos || '—'} documentos</strong>
          <small>{fuentesIndexadas || '—'} fragmentos preparados para consulta</small>
        </div>
        <div class="sidebar-foot"><span class="mini-shield">✓</span><span>Las respuestas incluyen referencias para que puedas contrastarlas.</span></div>
      </aside>

      <section class="main-panel">
        {#if pagina === 'chat'}
          <div class="panel-heading">
            <div>
              <div class="crumb">ASISTENTE <span>/</span> <b>CONSULTA DOCUMENTAL</b></div>
              <h2>¿Qué necesitas organizar?</h2>
              <p>Pregunta sobre planificación, trámites, prevención o emplazamientos.</p>
            </div>
            <button class="quiet-button" onclick={limpiarConversacion} disabled={mensajes.length === 0 || enviando} aria-label="Limpiar conversación">
              <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 5.5h12M8 5.5V3.8h4v1.7m2.5 0-.5 10.7H6L5.5 5.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M8.5 8.5v5M11.5 8.5v5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
              Limpiar
            </button>
          </div>

          <div class="chat-layout">
            <div class="conversation-column">
              <div class="disclosure">
                <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M10 2.5 17 6v4.2c0 3.7-2.7 6.3-7 7.8-4.3-1.5-7-4.1-7-7.8V6l7-3.5Z" stroke="currentColor" stroke-width="1.4"/><path d="M10 7v3.5m0 2.4v.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                <span><strong>Orientación documental.</strong> Cada respuesta se apoya en fragmentos de las fuentes disponibles; si no consta el dato, el asistente lo indicará.</span>
              </div>

              <div class="conversation" bind:this={conversacion} aria-live="polite" aria-label="Conversación">
                {#if mensajes.length === 0}
                  <div class="empty-chat">
                    <div class="empty-art" aria-hidden="true"><span class="art-sun"></span><span class="art-mountain mountain-back"></span><span class="art-mountain mountain-front"></span><span class="art-path"></span></div>
                    <p class="empty-kicker">TU ASISTENTE DE ACTIVIDADES</p>
                    <h3>Empieza por tu pregunta.</h3>
                    <p class="empty-copy">Consultaré las fuentes disponibles y te mostraré los fragmentos que respaldan la respuesta.</p>
                    <div class="suggestions" aria-label="Preguntas para empezar">
                      {#each sugerencias as sugerencia}
                        <button class="suggestion" onclick={() => void enviar(sugerencia)} disabled={enviando}>
                          <span>{sugerencia}</span><span class="suggestion-arrow" aria-hidden="true">↗</span>
                        </button>
                      {/each}
                    </div>
                  </div>
                {:else}
                  <div class="day-divider"><span>Conversación</span></div>
                  {#each mensajes as mensaje (mensaje.id)}
                    <article class="turn" class:user-turn={mensaje.role === 'user'}>
                      {#if mensaje.role === 'user'}
                        <div class="user-line"><div class="user-bubble">{mensaje.content}</div></div>
                      {:else}
                        <div class="answer-card" class:no-consta={mensaje.no_consta}>
                          <div class="answer-head">
                            <div class="assistant-name"><span class="assistant-mark" aria-hidden="true">✦</span><strong>Brújula</strong>{#if mensaje.no_consta}<span class="coverage-badge">No consta</span>{:else if !mensaje.pending}<span class="source-badge">Con fuentes</span>{/if}</div>
                            <span class="answer-context">Basado en la biblioteca</span>
                          </div>
                          {#if mensaje.pending}
                            <div class="typing"><span></span><span></span><span></span><em>Consultando documentos…</em></div>
                          {:else}
                            <p class="answer-text">{mensaje.content}</p>
                            {#if mensaje.no_consta}
                              <div class="not-found-notice">
                                <span class="not-found-icon" aria-hidden="true">!</span>
                                <div><strong>Dato no cubierto por las fuentes</strong><p>No hay una serie estadística o un registro disponible para acreditar esa cifra. El asistente no la estima.</p></div>
                              </div>
                            {:else if mensaje.fuentes?.length}
                              <div class="sources-block">
                                <div class="sources-title"><span>Fuentes consultadas</span><span>{mensaje.fuentes.length} fragmentos</span></div>
                                <div class="sources-list">
                                  {#each mensaje.fuentes as fuente, indice (`${mensaje.id}-${fuente.id}-${indice}`)}
                                    <a class="source-card" href={fuente.url} target="_blank" rel="noreferrer">
                                      <div class="source-top"><span class="source-index">{indice + 1}</span><span class="source-label">{fuente.id}</span><span class="source-open" aria-hidden="true">↗</span></div>
                                      <strong>{fuente.titulo}</strong>
                                      <span class="source-fragment">{fuente.fragmento}</span>
                                    </a>
                                  {/each}
                                </div>
                              </div>
                            {/if}
                          {/if}
                        </div>
                      {/if}
                    </article>
                  {/each}
                {/if}
              </div>

              {#if errorChat}
                <div class="inline-error" role="alert"><span>!</span>{errorChat}</div>
              {/if}

              <div class="composer-wrap">
                <form class="composer" onsubmit={alEnviar}>
                  <label class="sr-only" for="question-input">Escribe tu pregunta</label>
                  <textarea id="question-input" bind:value={pregunta} onkeydown={alEscribir} placeholder="Escribe tu pregunta sobre el campamento…" rows="1" disabled={enviando}></textarea>
                  <button class="send-button" type="submit" disabled={enviando || !pregunta.trim()} aria-label="Enviar pregunta">
                    {#if enviando}<span class="send-spinner"></span>{:else}<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m3 9 14-6-5.5 14-2.8-5.7L3 9Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="m8.7 11.3 3.5-3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>{/if}
                  </button>
                </form>
                <p class="composer-note">Intro para enviar · Mayús + Intro para una nueva línea</p>
              </div>
            </div>

            <aside class="chat-aside">
              <section class="aside-card">
                <div class="aside-card-heading"><span class="aside-icon green">⌕</span><h3>Alcance de consulta</h3></div>
                <ul class="scope-list"><li><span>✓</span> Normativa y guías de Juventud JCyL</li><li><span>✓</span> Trámites y documentación de actividades</li><li><span>✓</span> Prevención, riesgos e incidencias</li><li><span>✓</span> Fichas públicas de instalaciones</li></ul>
              </section>
              <section class="aside-card aside-highlight">
                <div class="aside-card-heading"><span class="aside-icon amber">!</span><h3>Si falta un dato</h3></div>
                <p>El asistente te avisará cuando la biblioteca no permita responder, en vez de completar la información por su cuenta.</p>
              </section>
              <button class="aside-link-card" onclick={() => cambiarPagina('documentos')}>
                <span class="aside-link-icon"><svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M5 2.8h7l3 3v11.4H5V2.8Z" stroke="currentColor" stroke-width="1.5"/><path d="M12 3v3h3M7.5 9h5M7.5 12h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg></span>
                <span><strong>Explorar documentos</strong><small>{totalDocumentos || '…'} fuentes en la biblioteca</small></span><span class="link-arrow">→</span>
              </button>
            </aside>
          </div>
        {:else}
          <div class="panel-heading docs-heading">
            <div>
              <div class="crumb">BIBLIOTECA <span>/</span> <b>FUENTES</b></div>
              <h2>Documentos y registros</h2>
              <p>Busca entre las fuentes incorporadas al asistente y abre el original.</p>
            </div>
            <span class="library-total"><strong>{totalDocumentos}</strong><small>fuentes</small></span>
          </div>

          <div class="library-intro">
            <span class="library-icon"><svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M3.5 4.5c2.4-1 4.7-.8 6.5.4v11c-1.8-1.2-4.1-1.4-6.5-.4v-11Zm13 0c-2.4-1-4.7-.8-6.5.4v11c1.8-1.2 4.1-1.4 6.5-.4v-11Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg></span>
            <p><strong>Fuentes consultables</strong><span>Contenido público extraído para la búsqueda semántica. Las fichas externas pueden cambiar; consulta el documento original antes de tramitar.</span></p>
          </div>

          <div class="library-toolbar">
            <div class="search-box"><svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="8.8" cy="8.8" r="5.4" stroke="currentColor" stroke-width="1.5"/><path d="m13 13 4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg><label class="sr-only" for="doc-search">Buscar documentos</label><input id="doc-search" bind:value={consultaDocs} oninput={buscarDocumentos} placeholder="Buscar por título, tema o identificador…" /></div>
            <label class="filter-select"><span class="sr-only">Filtrar por tipo</span><select bind:value={tipoDoc} onchange={() => void cargarDocumentos()}><option value="">Todos los tipos</option><option value="PDF">PDF oficial</option><option value="Portal">Portal</option><option value="Directorio">Directorio</option></select><span aria-hidden="true">⌄</span></label>
          </div>
          <div class="result-line"><span>{cargandoDocs ? 'Actualizando resultados…' : `${totalDocumentos} ${totalDocumentos === 1 ? 'resultado' : 'resultados'}`}</span><span>Ordenados según la biblioteca</span></div>

          {#if errorDocs}
            <div class="library-error" role="alert"><span>!</span><div><strong>No se pudo cargar la biblioteca.</strong><small>{errorDocs} Comprueba que el servidor Python está iniciado.</small></div></div>
          {:else if cargandoDocs && documentos.length === 0}
            <div class="loading-docs"><span class="send-spinner"></span> Cargando documentos…</div>
          {:else if documentos.length === 0}
            <div class="no-results"><span>⌕</span><strong>No hay documentos con esos filtros.</strong><small>Prueba con otra palabra o selecciona «Todos los tipos».</small></div>
          {:else}
            <div class="document-list" aria-label="Listado de documentos">
              {#each documentos as documento (documento.id)}
                <article class="document-row">
                  <span class="document-icon" class:portal-icon={documento.tipo.includes('Portal')} class:directory-icon={documento.tipo === 'Directorio'}>
                    {#if documento.tipo.includes('Portal')}<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.4"/><path d="M7.7 7.4a2.4 2.4 0 1 1 4.1 1.7c-1 .9-1.8 1.2-1.8 2.4m0 2v.1" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>{:else if documento.tipo === 'Directorio'}<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m3 16 5-9 3 5 2-3 4 7H3Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>{:else}<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 2.8h8l4 4v10.4H4V2.8Z" stroke="currentColor" stroke-width="1.4"/><path d="M12 3v4h4M7 10h6M7 13h6" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>{/if}
                  </span>
                  <div class="document-main"><div class="document-kicker"><span>{documento.id}</span><span class="type-tag" class:portal-tag={documento.tipo.includes('Portal')} class:directory-tag={documento.tipo === 'Directorio'}>{documento.tipo}</span></div><h3>{documento.titulo}</h3><p>{documento.cobertura}</p><div class="document-meta"><span>{documento.fragmentos_indexados} fragmentos indexados</span>{#if documento.fecha_actualizacion}<span>Actualizado: {documento.fecha_actualizacion}</span>{/if}</div></div>
                  <a class="open-source" href={documento.url} target="_blank" rel="noreferrer" aria-label={`Abrir fuente: ${documento.titulo}`}>Abrir fuente <span aria-hidden="true">↗</span></a>
                </article>
              {/each}
            </div>
          {/if}
          <div class="library-footnote"><span>i</span>Los documentos oficiales enlazados son la referencia. La indexación facilita encontrarlos, pero no sustituye su lectura.</div>
        {/if}
      </section>
    </div>

    <footer class="site-footer"><span>Brújula <i>·</i> Asistente documental de tiempo libre</span><span>Fuentes: <a href="https://juventud.jcyl.es/web/es/actividades-tiempo-libre/organizacion-gestion-campamentos.html" target="_blank" rel="noreferrer">Juventud JCyL</a> <i>·</i> <a href="https://servicios.jcyl.es/wiri/?inicio=ayuda" target="_blank" rel="noreferrer">Ayuda WIRI</a></span></footer>
  </main>
</div>
