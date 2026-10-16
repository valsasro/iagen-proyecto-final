"""Descarga y extrae el contenido público de las fuentes de Juventud JCyL."""

from __future__ import annotations

import html
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CORPUS_PATH = DATA_DIR / "corpus.json"
INDICE_URL = "https://juventud.jcyl.es/web/es/actividades-tiempo-libre/organizacion-gestion-campamentos.html"
WIRI_URL = "https://servicios.jcyl.es/wiri/?inicio=ayuda"
DIRECTORIO_URL = (
    "https://juventud.jcyl.es/web/jcyl/Juventud/es/Plantilla100Detalle/"
    "1284710993928/_/1284167019168/Albergue"
)


class PaginaParser(HTMLParser):
    """Extrae enlaces PDF y texto visible, omitiendo scripts y estilos."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.visible: list[str] = []
        self._href: str | None = None
        self._anchor_text: list[str] = []
        self._hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag.lower() in {"script", "style", "noscript"}:
            self._hidden += 1
        if tag.lower() == "a":
            self._href = attrs_map.get("href")
            self._anchor_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(self._anchor_text)))
            self._href = None
            self._anchor_text = []
        if tag in {"script", "style", "noscript"} and self._hidden:
            self._hidden -= 1

    def handle_data(self, data: str) -> None:
        clean = re.sub(r"\s+", " ", data).strip()
        if not clean:
            return
        if self._href:
            self._anchor_text.append(clean)
        if not self._hidden:
            self.visible.append(clean)


def cargar_configuracion() -> None:
    load_dotenv(ROOT / ".env", override=False)
    # urllib y OpenAI/httpx leen estas variables. No se imprime ningún valor.
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or proxy
    if proxy:
        os.environ.setdefault("HTTPS_PROXY", proxy)
    if http_proxy:
        os.environ.setdefault("HTTP_PROXY", http_proxy)


def descargar(url: str, max_bytes: int = 40_000_000) -> tuple[bytes, str | None]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BrujulaCampamentos/1.0 (lector documental)"},
    )
    # ProxyHandler respeta NO_PROXY/no_proxy del entorno; si no hay proxy,
    # conecta directamente según la configuración de urllib.
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError(f"La fuente supera el límite permitido: {url}")
        return data, response.headers.get("Last-Modified")


def parsear_pagina(contenido: bytes, url: str) -> PaginaParser:
    parser = PaginaParser()
    parser.feed(contenido.decode("utf-8", errors="replace"))
    parser.close()
    # Resolver enlaces relativos y decodificar entidades del atributo HTML.
    parser.links = [
        (urllib.parse.urljoin(url, html.unescape(href)), title.strip())
        for href, title in parser.links
    ]
    return parser


def texto_pdf(contenido: bytes) -> str:
    reader = PdfReader(io.BytesIO(contenido))
    paginas: list[str] = []
    for pagina in reader.pages:
        texto = pagina.extract_text(extraction_mode="layout") or pagina.extract_text() or ""
        texto = re.sub(r"[\t\u00a0 ]+", " ", texto)
        texto = re.sub(r" *\n *", "\n", texto)
        texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
        if texto:
            paginas.append(texto)
    return "\n\n".join(paginas).strip()


def id_documento(titulo: str, nombre: str, fallback: int) -> str:
    def normalizar(valor: str) -> str:
        valor = unicodedata.normalize("NFKD", valor).casefold()
        valor = "".join(c for c in valor if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", " ", valor).strip()

    combinado = normalizar(f"{titulo} {nombre}")
    reglas = [
        ("ley 11/2002", "DOC-001"),
        # La orden modificadora cita a FAM/203/2016 en su título: va antes.
        ("orden fam 688 2021", "DOC-004"),
        ("orden fam 203 2016", "DOC-002"),
        ("orden fam 614 2016", "DOC-003"),
        ("decreto 117 2003", "DOC-005"),
        ("parajes", "DOC-006"),
        ("guia de uso para organizadores", "DOC-007"),
        ("guia de uso para evaluadores", "DOC-008"),
        ("eval - solicitud", "DOC-009"),
        ("instrucciones para cumplimentar", "DOC-010"),
        ("anexo 1", "DOC-011"),
        ("anexo 2", "DOC-012"),
        ("anexo 3", "DOC-013"),
        ("anexo 4", "DOC-014"),
        ("anexo 5", "DOC-015"),
        ("guia para usuarios", "DOC-016"),
        ("comunicacion previa en papel", "DOC-017"),
        ("modificacion comunicacion", "DOC-018"),
        ("cancelacion comunicacion", "DOC-019"),
        ("hoja de incidencias", "DOC-020"),
        ("ratio de responsables", "DOC-021"),
    ]
    for patron, doc_id in reglas:
        if normalizar(patron) in combinado:
            return doc_id
    return f"DOC-{fallback:03d}"


def documento_web(
    *,
    doc_id: str,
    titulo: str,
    url: str,
    tipo: str,
    cobertura: str,
    pausa_segundos: float = 0.0,
) -> dict[str, object]:
    if pausa_segundos > 0:
        time.sleep(pausa_segundos)
    contenido, fecha = descargar(url)
    pagina = parsear_pagina(contenido, url)
    texto = "\n".join(pagina.visible)
    return {
        "id": doc_id,
        "titulo": titulo,
        "url": url,
        "tipo": tipo,
        "fecha_actualizacion": fecha,
        "cobertura": cobertura,
        "texto": texto,
        "indexable": bool(texto.strip()),
    }


def generar_corpus() -> dict[str, object]:
    cargar_configuracion()
    html_indice, fecha_indice = descargar(INDICE_URL)
    pagina_indice = parsear_pagina(html_indice, INDICE_URL)
    pdfs: list[tuple[str, str]] = []
    vistos: set[str] = set()
    for url, titulo in pagina_indice.links:
        if not re.search(r"\.pdf(?:$|[?#])", url, flags=re.IGNORECASE):
            continue
        if url not in vistos:
            pdfs.append((url, titulo))
            vistos.add(url)
    if not pdfs:
        raise RuntimeError("La página oficial no contiene enlaces PDF accesibles.")

    documentos: list[dict[str, object]] = []
    for numero, (url, titulo) in enumerate(pdfs, start=1):
        pdf, fecha = descargar(url)
        texto = texto_pdf(pdf)
        nombre = urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).name)
        titulo = re.sub(r"\s+", " ", html.unescape(titulo)).strip()
        titulo = re.sub(
            r"\s*\(\s*[\d.,]+\s*kbytes?\s*\)\s*$", "", titulo, flags=re.IGNORECASE
        ).strip()
        if not titulo:
            titulo = nombre.removesuffix("_metadata.pdf").replace("_", " ")
        doc_id = id_documento(titulo, nombre, numero)
        documentos.append(
            {
                "id": doc_id,
                "titulo": titulo,
                "url": url,
                "tipo": "PDF",
                "fecha_actualizacion": fecha,
                "cobertura": "Documento oficial de Juventud JCyL",
                "texto": texto,
                "indexable": len(texto) >= 40,
                "nombre_archivo": nombre,
            }
        )
        print(f"Extraído {doc_id}: {len(texto):,} caracteres")

    # La página de ayuda de WIRI es pública pero solo presenta la entrada
    # anónima; se conserva su texto real y no se inventan artículos internos.
    wiri = documento_web(
        doc_id="PORTAL-001",
        titulo="WIRI · Inspección, Registro, Instrucción y Seguimiento",
        url=WIRI_URL,
        tipo="Portal de ayuda",
        cobertura="Entrada pública de la aplicación",
        pausa_segundos=1.0,
    )
    documentos.append(wiri)

    # Ficha adicional enlazada como fuente en la maqueta para responder sobre
    # emplazamientos, comprobada en el directorio oficial de Juventud.
    directorio = documento_web(
        doc_id="DIR-001",
        titulo="Campamento juvenil · ficha del directorio de Juventud",
        url=DIRECTORIO_URL,
        tipo="Directorio",
        cobertura="Ficha pública de instalación juvenil",
    )
    documentos.append(directorio)

    documentos.sort(key=lambda documento: str(documento["id"]))

    return {
        "version": 1,
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "fuentes_indice": [{"url": INDICE_URL, "fecha": fecha_indice}],
        "documentos": documentos,
    }


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    corpus = generar_corpus()
    temp_path = CORPUS_PATH.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp_path.replace(CORPUS_PATH)
    indexables = sum(bool(doc["indexable"]) for doc in corpus["documentos"])
    print(
        f"Corpus guardado: {CORPUS_PATH.relative_to(ROOT)} · "
        f"{len(corpus['documentos'])} documentos, {indexables} con texto indexable."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"No se pudo preparar el corpus: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
