from __future__ import annotations

import os
import csv
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(os.environ.get("WTW_PROJECT_ROOT", Path.cwd())).resolve()
OUT = ROOT / "06_manuscript" / "references"

PMIDS = [
    "27145814", "39776348", "39395660", "29089921", "27856146",
    "23186037", "39352612", "37966330", "38335145", "42023254",
    "40617611", "39585965", "40136231", "15312228", "35648198",
    "30113379", "39982143", "23180503", "32068366", "23344834",
    "23863230", "20116842", "36596836", "30204154", "40903028",
    "17938389", "26440803", "26994063", "27237061", "36943798",
    "37660025", "19000302", "40659406",
]


def node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def fetch_xml(pmids: list[str]) -> bytes:
    params = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + params
    req = urllib.request.Request(url, headers={"User-Agent": "WHEN-TO-WAKE-ABI/1.0 research reference audit"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def parse_article(article: ET.Element) -> dict[str, object]:
    citation = article.find("MedlineCitation")
    pubmed_data = article.find("PubmedData")
    art = citation.find("Article") if citation is not None else None
    journal = art.find("Journal") if art is not None else None
    journal_issue = journal.find("JournalIssue") if journal is not None else None
    pub_date = journal_issue.find("PubDate") if journal_issue is not None else None
    pmid = node_text(citation.find("PMID")) if citation is not None else ""
    title = node_text(art.find("ArticleTitle")) if art is not None else ""
    journal_title = node_text(journal.find("Title")) if journal is not None else ""
    iso_abbrev = node_text(journal.find("ISOAbbreviation")) if journal is not None else ""
    year = node_text(pub_date.find("Year")) if pub_date is not None else ""
    if not year and pub_date is not None:
        medline_date = node_text(pub_date.find("MedlineDate"))
        year = medline_date[:4]
    volume = node_text(journal_issue.find("Volume")) if journal_issue is not None else ""
    issue = node_text(journal_issue.find("Issue")) if journal_issue is not None else ""
    pages = node_text(art.find("Pagination/MedlinePgn")) if art is not None else ""
    language = node_text(art.find("Language")) if art is not None else ""
    authors: list[dict[str, str]] = []
    if art is not None:
        for author in art.findall("AuthorList/Author"):
            collective = node_text(author.find("CollectiveName"))
            if collective:
                authors.append({"family": collective, "given": "", "initials": "", "collective": "1"})
            else:
                authors.append({
                    "family": node_text(author.find("LastName")),
                    "given": node_text(author.find("ForeName")),
                    "initials": node_text(author.find("Initials")),
                    "collective": "0",
                })
    identifiers: dict[str, str] = {}
    if pubmed_data is not None:
        for aid in pubmed_data.findall("ArticleIdList/ArticleId"):
            identifiers[aid.attrib.get("IdType", "")] = node_text(aid)
    doi = identifiers.get("doi", "")
    pmc = identifiers.get("pmc", "")
    return {
        "pmid": pmid,
        "title": title,
        "journal": journal_title,
        "journal_abbrev": iso_abbrev,
        "year": year,
        "volume": volume,
        "issue": issue,
        "pages": pages,
        "doi": doi,
        "pmc": pmc,
        "language": language,
        "authors": authors,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    }


def ris_record(item: dict[str, object]) -> str:
    lines = ["TY  - JOUR"]
    for author in item["authors"]:
        if author["collective"] == "1":
            value = author["family"]
        else:
            value = f"{author['family']}, {author['given']}".strip(", ")
        lines.append(f"AU  - {value}")
    fields = [
        ("TI", item["title"]), ("JO", item["journal_abbrev"] or item["journal"]),
        ("PY", item["year"]), ("VL", item["volume"]), ("IS", item["issue"]),
        ("SP", item["pages"]), ("DO", item["doi"]), ("AN", item["pmid"]),
        ("UR", item["pubmed_url"]),
    ]
    for tag, value in fields:
        if value:
            lines.append(f"{tag}  - {value}")
    lines.append("ER  -")
    return "\n".join(lines)


def vancouver(item: dict[str, object]) -> str:
    names = []
    for author in item["authors"]:
        if author["collective"] == "1":
            names.append(author["family"])
        else:
            names.append((author["family"] + " " + author["initials"]).strip())
    if len(names) > 6:
        author_text = ", ".join(names[:6]) + ", et al."
    else:
        author_text = ", ".join(names) + "."
    citation = f"{author_text} {item['title']} {item['journal_abbrev'] or item['journal']}. {item['year']}"
    if item["volume"]:
        citation += f";{item['volume']}"
        if item["issue"]:
            citation += f"({item['issue']})"
    if item["pages"]:
        citation += f":{item['pages']}"
    citation += "."
    if item["doi"]:
        citation += f" doi:{item['doi']}."
    return citation.replace("..", ".")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = fetch_xml(PMIDS)
    (OUT / "pubmed_efetch_snapshot_2026-08-02.xml").write_bytes(payload)
    root = ET.fromstring(payload)
    items = [parse_article(article) for article in root.findall("PubmedArticle")]
    by_pmid = {str(item["pmid"]): item for item in items}
    missing = [pmid for pmid in PMIDS if pmid not in by_pmid]
    if missing:
        raise RuntimeError("PMIDs not returned by PubMed: " + ", ".join(missing))
    ordered = [by_pmid[pmid] for pmid in PMIDS]

    (OUT / "references_pubmed.ris").write_text("\n\n".join(ris_record(item) for item in ordered) + "\n", encoding="utf-8")
    (OUT / "references_vancouver.txt").write_text("\n".join(f"{i}. {vancouver(item)}" for i, item in enumerate(ordered, 1)) + "\n", encoding="utf-8")
    flat_rows = []
    for item in ordered:
        row = {k: v for k, v in item.items() if k != "authors"}
        row["authors"] = "; ".join((a["family"] if a["collective"] == "1" else f"{a['family']}, {a['given']}") for a in item["authors"])
        flat_rows.append(row)
    with (OUT / "references_pubmed.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0].keys()))
        writer.writeheader()
        writer.writerows(flat_rows)
    log = {
        "accessed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "NCBI PubMed EFetch API",
        "pmids_requested": PMIDS,
        "pmids_returned": [item["pmid"] for item in ordered],
        "record_count": len(ordered),
        "missing": missing,
        "validation": "Returned PMID, title, journal, year, DOI, and author fields preserved in CSV/RIS/XML snapshot.",
    }
    (OUT / "REFERENCE_FETCH_LOG.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
