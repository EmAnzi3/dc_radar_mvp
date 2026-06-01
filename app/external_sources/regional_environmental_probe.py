from __future__ import annotations

import csv
import html
import re
import time
from collections import deque
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests


SOURCES = Path("data/input/external_sources/regional_environmental_sources.csv")
KNOWN_PROJECTS = Path("data/output/dc_project_fused_master.csv")

OUT_CSV = Path("data/output/external_sources/regional_environmental_candidates.csv")
OUT_HTML = Path("reports/site/external_sources/regional_environmental_candidates.html")

MAX_PAGES_PER_SOURCE = 80
MAX_DEPTH = 1
SLEEP_SECONDS = 0.5

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"

STRONG_TERMS = [
    "data center",
    "datacenter",
    "centro elaborazione dati",
    "server farm",
    "hyperscale",
]

SUPPORT_TERMS = [
    "cloud",
    "generatori di emergenza",
    "gruppi elettrogeni",
    "potenza termica",
    "cabina elettrica",
    "impianti tecnologici",
    "impianti tecnici",
    "continuità elettrica",
    "continuita elettrica",
    "raffreddamento",
    "district cooling",
    "teleriscaldamento",
    "VIA",
    "verifica di assoggettabilità",
    "verifica assoggettabilità",
    "VAS",
    "PAUR",
    "art. 23",
    "art.19",
    "d.lgs. 152",
    "proponente",
    "comune",
    "provincia",
    "elaborati progettuali",
    "conferenza dei servizi",
    "SUAP",
    "SUE",
    "SCIA",
    "permesso di costruire",
]

URL_KEEP_TERMS = [
    "via",
    "vas",
    "valutazione",
    "impatto",
    "ambientale",
    "progetti",
    "procedimenti",
    "silvia",
    "data-center",
    "datacenter",
    "documentazione",
    "elaborati",
    "download",
    "pdf",
]


def clean(value: object) -> str:
    return str(value or "").strip()


def norm(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9àèéìòù]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def canonical_url(url: str) -> str:
    url, _ = urldefrag(clean(url))
    return url


def safe_join(base_url: str, href: str) -> str:
    href = clean(href)
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return ""

    try:
        url = canonical_url(urljoin(base_url, href))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        return url
    except Exception:
        return ""


def same_host(a: str, b: str) -> bool:
    return urlparse(a).netloc.lower() == urlparse(b).netloc.lower()


def skip_url(url: str) -> bool:
    low = clean(url).lower()
    return low.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".css", ".js", ".ico", ".zip", ".rar", ".7z"))


def url_score(url: str) -> int:
    low = clean(url).lower()
    return sum(1 for term in URL_KEEP_TERMS if term in low)


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<script.*?</script>", " ", raw)
    raw = re.sub(r"(?is)<style.*?</style>", " ", raw)
    raw = re.sub(r"(?is)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return re.sub(r"\s+", " ", raw).strip()


def pdf_to_text(content: bytes) -> str:
    try:
        import fitz  # type: ignore
        doc = fitz.open(stream=content, filetype="pdf")
        return "\n".join(page.get_text("text") for page in doc)
    except Exception:
        pass

    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def extract_links(base_url: str, raw_html: str) -> list[str]:
    links = []

    try:
        from bs4 import BeautifulSoup  # type: ignore
        soup = BeautifulSoup(raw_html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = safe_join(base_url, a.get("href", ""))
            if href and href not in links:
                links.append(href)
    except Exception:
        for m in re.finditer(r'href=["\']([^"\']+)["\']', raw_html, re.I):
            href = safe_join(base_url, html.unescape(m.group(1)))
            if href and href not in links:
                links.append(href)

    return links


def fetch(url: str) -> tuple[str, list[str], str, str]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
    except Exception as e:
        return "", [], "", str(e)

    content_type = r.headers.get("content-type", "").lower()
    low = clean(url).lower()

    if "pdf" in content_type or low.endswith(".pdf"):
        text = pdf_to_text(r.content)
        if not text:
            return "", [], content_type, "pdf_text_extraction_failed"
        return re.sub(r"\s+", " ", text).strip(), [], content_type, ""

    raw = r.text
    return html_to_text(raw), extract_links(url, raw), content_type, ""


def find_terms(text_norm: str, terms: list[str]) -> list[str]:
    out = []
    for term in terms:
        if norm(term) in text_norm and term not in out:
            out.append(term)
    return out


def best_snippet(text: str, terms: list[str]) -> str:
    for term in terms:
        m = re.search(re.escape(term), text, re.I)
        if m:
            start = max(0, m.start() - 500)
            end = min(len(text), m.end() + 500)
            return re.sub(r"\s+", " ", text[start:end]).strip()
    return text[:1000]


def load_known_terms() -> list[str]:
    terms = []

    banned = {
        "roma",
        "milano",
        "lazio",
        "lombardia",
        "data center",
        "datacenter",
        "cloud",
        "aruba",
        "stack",
        "apto",
        "aws",
    }

    for r in read_csv(KNOWN_PROJECTS):
        for field in [
            "project",
            "mase_proponent",
        ]:
            value = clean(r.get(field))

            if not value:
                continue

            if value.lower() == "da identificare":
                continue

            if value.lower() in banned:
                continue

            # Evita match troppo corti/generici.
            if len(value) < 8:
                continue

            # Evita operatori singoli troppo ambigui.
            if len(value.split()) == 1 and len(value) < 12:
                continue

            if value not in terms:
                terms.append(value)

    return terms


def is_reference_page(text_norm: str, url: str, source: dict[str, str]) -> bool:
    source_type = norm(source.get("source_type"))
    low_url = clean(url).lower()

    if source_type in {"policy_data_center", "via_info"}:
        return True

    reference_markers = [
        "linee guida",
        "istruzioni",
        "procedura attivazione",
        "attivazione nuova procedura",
        "motore di ricerca",
        "valutazione impatto ambientale progetti",
        "valutazione ambientale strategica",
        "registro impianti biomasse",
        "registro impianti geotermici",
        "sostenibilita energetica",
        "sostenibilità energetica",
        "inquinamento elettromagnetico",
    ]

    if any(marker in text_norm for marker in reference_markers):
        return True

    url_markers = [
        "procedura-attivazione",
        "istruzioni",
        "registro-impianti",
        "sostenibilita-energetica",
        "inquinamento-elettromagnetico",
    ]

    return any(marker in low_url for marker in url_markers)


def has_compound_dc_signal(text_norm: str) -> bool:
    has_cloud = "cloud" in text_norm

    has_generator_context = any(term in text_norm for term in [
        "generatori di emergenza",
        "gruppi elettrogeni",
        "potenza termica",
    ])

    return has_cloud and has_generator_context


def classify(text: str, known_terms: list[str], source: dict[str, str], url: str) -> tuple[str, list[str], list[str], list[str], str]:
    text_norm = norm(text)

    strong = find_terms(text_norm, STRONG_TERMS)
    support = find_terms(text_norm, SUPPORT_TERMS)
    known = find_terms(text_norm, known_terms)

    compound_signal = has_compound_dc_signal(text_norm)
    reference_page = is_reference_page(text_norm, url, source)

    # Nessun segnale DC reale.
    if not strong and not compound_signal:
        return "discard_or_low_relevance", [], support, known, ""

    if compound_signal and "cloud + generatori/potenza termica" not in strong:
        strong.append("cloud + generatori/potenza termica")

    # Linee guida, istruzioni o pagine informative: utili come reference, non candidati.
    if reference_page:
        snippet = best_snippet(text, strong + support)
        return "reference_policy_review", strong, support, known, snippet

    if known:
        status = "known_project_match_review"
    else:
        status = "new_candidate_review"

    snippet = best_snippet(text, strong + known + support)
    return status, strong, support, known, snippet

def crawl_source(source: dict[str, str], known_terms: list[str]) -> list[dict[str, str]]:
    start = canonical_url(source.get("start_url"))
    queue = deque([(start, 0)])
    seen = set()
    out = []
    processed = 0

    while queue and processed < MAX_PAGES_PER_SOURCE:
        url, depth = queue.popleft()
        url = canonical_url(url)

        if not url or url in seen or skip_url(url):
            continue

        if not same_host(url, start):
            continue

        seen.add(url)

        text, links, content_type, error = fetch(url)
        processed += 1

        if text:
            status, strong, support, known, snippet = classify(text, known_terms, source, url)

            if status != "discard_or_low_relevance":
                out.append({
                    "region": clean(source.get("region")),
                    "source_system": clean(source.get("source_system")),
                    "source_type": clean(source.get("source_type")),
                    "candidate_status": status,
                    "strong_terms": " | ".join(strong),
                    "support_terms": " | ".join(support),
                    "known_matches": " | ".join(known[:12]),
                    "source_url": url,
                    "snippet": snippet,
                    "content_type": content_type,
                    "fetch_error": error,
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                })

        if depth < MAX_DEPTH:
            ranked = sorted(
                [link for link in links if same_host(link, start) and not skip_url(link)],
                key=url_score,
                reverse=True,
            )

            for link in ranked:
                if link not in seen and (depth == 0 or url_score(link) > 0):
                    queue.append((link, depth + 1))

        time.sleep(SLEEP_SECONDS)

    return out


def render_html(rows: list[dict[str, str]]) -> str:
    def e(value: object) -> str:
        return html.escape(clean(value))

    trs = []

    for r in rows:
        trs.append(f"""
        <tr>
          <td>{e(r["region"])}</td>
          <td>{e(r["source_system"])}</td>
          <td>{e(r["source_type"])}</td>
          <td>{e(r["candidate_status"])}</td>
          <td>{e(r["strong_terms"])}</td>
          <td>{e(r["known_matches"])}</td>
          <td><a href="{e(r["source_url"])}" target="_blank" rel="noopener">apri</a></td>
          <td>{e(r["snippet"])}</td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Regional Environmental Candidates</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#f5f7fb; color:#172033; }}
header {{ background:linear-gradient(135deg,#08111f,#0f4c81); color:white; padding:24px 30px; }}
main {{ max-width:1500px; margin:0 auto; padding:20px; }}
.panel {{ background:white; border:1px solid #dfe4ea; border-radius:14px; padding:16px; overflow:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ border-bottom:1px solid #e5e7eb; padding:8px; vertical-align:top; text-align:left; }}
th {{ color:#667085; font-size:11px; text-transform:uppercase; }}
a {{ color:#0f4c81; font-weight:700; }}
</style>
</head>
<body>
<header>
<h1>Regional Environmental Candidates</h1>
<p>Review-only: Lombardia/Lazio VIA-VAS probe · {e(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<section class="panel">
<table>
<thead>
<tr>
<th>Regione</th><th>Sistema</th><th>Tipo</th><th>Status</th><th>Strong terms</th><th>Known matches</th><th>URL</th><th>Snippet</th>
</tr>
</thead>
<tbody>
{''.join(trs)}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def main() -> None:
    sources = read_csv(SOURCES)
    known_terms = load_known_terms()

    all_rows = []

    for source in sources:
        print(f"[INFO] Regional probe: {clean(source.get('region'))} / {clean(source.get('source_system'))}")
        all_rows.extend(crawl_source(source, known_terms))

    fields = [
        "region",
        "source_system",
        "source_type",
        "candidate_status",
        "strong_terms",
        "support_terms",
        "known_matches",
        "source_url",
        "snippet",
        "content_type",
        "fetch_error",
        "checked_at",
    ]

    write_csv(OUT_CSV, all_rows, fields)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(all_rows), encoding="utf-8")

    print(f"[OK] Written {OUT_CSV} with {len(all_rows)} rows")
    print(f"[OK] Written {OUT_HTML}")


if __name__ == "__main__":
    main()
