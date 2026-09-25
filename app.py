import streamlit as st
import requests
import pandas as pd

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Bulk Backlink Checker",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 Bulk Backlink Checker")

st.write(
    "Proveri da li lista URL-ova sadrži link ka target domenu, "
    "kroz koji anchor tekst, ka kom URL-u link vodi i koje "
    "rel atribute backlink ima."
)

st.caption(
    "Status NE se prikazuje samo kada je stranica uspešno otvorena "
    "i target link nije pronađen. Ako stranici nije moguće pouzdano "
    "pristupiti, rezultat je NIJE MOGUĆE PROVERITI."
)


# =========================================================
# SETTINGS
# =========================================================

REQUEST_TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "sr-RS,sr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# =========================================================
# RESULT COLUMNS
# =========================================================

RESULT_COLUMNS = [
    "Source URL",
    "HTTP Status",
    "Status provere",
    "Link ka target domenu",
    "Anchor tekst",
    "Linkovani target URL",
    "Rel atribut",
    "Nofollow",
    "Sponsored",
    "UGC",
    "Link Type",
    "Napomena",
]


# =========================================================
# NORMALIZE DOMAIN
# =========================================================

def normalize_domain(value):

    value = str(value).strip().lower()

    if not value:
        return ""

    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    try:
        parsed = urlparse(value)
        domain = parsed.hostname or ""
    except Exception:
        return ""

    domain = domain.lower().strip(".")

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


# =========================================================
# GET LINK DOMAIN
# =========================================================

def get_link_domain(url):

    try:
        parsed = urlparse(url)
        domain = parsed.hostname or ""
    except Exception:
        return ""

    domain = domain.lower().strip(".")

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


# =========================================================
# CHECK TARGET DOMAIN
# =========================================================

def is_target_domain(href, target_domain):

    link_domain = get_link_domain(href)

    if not link_domain:
        return False

    # Exact domain
    if link_domain == target_domain:
        return True

    # Subdomain
    if link_domain.endswith("." + target_domain):
        return True

    return False


# =========================================================
# REL VALUES
# =========================================================

def get_rel_values(link):

    rel = link.get("rel", [])

    if not rel:
        return []

    if isinstance(rel, str):
        values = rel.lower().split()
    else:
        values = [
            str(value).strip().lower()
            for value in rel
            if str(value).strip()
        ]

    # Remove duplicates while preserving order
    return list(dict.fromkeys(values))


# =========================================================
# LINK TYPE
# =========================================================

def get_link_type(rel_values):

    types = []

    if "nofollow" in rel_values:
        types.append("NOFOLLOW")

    if "sponsored" in rel_values:
        types.append("SPONSORED")

    if "ugc" in rel_values:
        types.append("UGC")

    if not types:
        return "FOLLOW"

    return " + ".join(types)


# =========================================================
# ANCHOR TEXT
# =========================================================

def get_anchor_text(link):

    anchor = link.get_text(
        " ",
        strip=True
    )

    if anchor:
        return anchor

    # Image-only backlink
    image = link.find("img")

    if image:

        alt = image.get("alt", "").strip()

        if alt:
            return f"[IMAGE: {alt}]"

        return "[IMAGE LINK]"

    return "[EMPTY ANCHOR]"


# =========================================================
# STATUS ROW
# =========================================================

def create_status_row(
    source_url,
    http_status="",
    status_provere="",
    link_status="",
    napomena=""
):

    return {
        "Source URL": source_url,
        "HTTP Status": http_status,
        "Status provere": status_provere,
        "Link ka target domenu": link_status,
        "Anchor tekst": "",
        "Linkovani target URL": "",
        "Rel atribut": "",
        "Nofollow": "",
        "Sponsored": "",
        "UGC": "",
        "Link Type": "",
        "Napomena": napomena,
    }


# =========================================================
# CHECK SOURCE URL
# =========================================================

def check_url(source_url, target_domain):

    rows = []

    try:

        response = requests.get(
            source_url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        status_code = response.status_code

        # Used internally for relative URLs after redirects.
        final_source_url = response.url

        # =================================================
        # 403 FORBIDDEN
        # =================================================

        if status_code == 403:

            rows.append(
                create_status_row(
                    source_url=source_url,
                    http_status=status_code,
                    status_provere="NIJE MOGUĆE PROVERITI",
                    link_status="NIJE PROVERENO",
                    napomena=(
                        "Server je vratio HTTP 403 Forbidden. "
                        "Crawler nema pouzdan pristup stranici."
                    )
                )
            )

            return rows

        # =================================================
        # 429 TOO MANY REQUESTS
        # =================================================

        if status_code == 429:

            rows.append(
                create_status_row(
                    source_url=source_url,
                    http_status=status_code,
                    status_provere="NIJE MOGUĆE PROVERITI",
                    link_status="NIJE PROVERENO",
                    napomena=(
                        "Server je vratio HTTP 429 Too Many Requests. "
                        "Provera nije pouzdano izvršena."
                    )
                )
            )

            return rows

        # =================================================
        # SERVER ERRORS
        # =================================================

        if status_code >= 500:

            rows.append(
                create_status_row(
                    source_url=source_url,
                    http_status=status_code,
                    status_provere="NIJE MOGUĆE PROVERITI",
                    link_status="NIJE PROVERENO",
                    napomena=(
                        f"Server je vratio HTTP {status_code}. "
                        "Stranica nije mogla pouzdano da se proveri."
                    )
                )
            )

            return rows

        # =================================================
        # OTHER 4XX
        # =================================================

        if 400 <= status_code < 500:

            rows.append(
                create_status_row(
                    source_url=source_url,
                    http_status=status_code,
                    status_provere="NIJE MOGUĆE PROVERITI",
                    link_status="NIJE PROVERENO",
                    napomena=(
                        f"Server je vratio HTTP {status_code}. "
                        "Stranica nije uspešno otvorena, pa backlink "
                        "nije moguće pouzdano proveriti."
                    )
                )
            )

            return rows

        # =================================================
        # UNEXPECTED STATUS
        # =================================================

        if status_code < 200 or status_code >= 400:

            rows.append(
                create_status_row(
                    source_url=source_url,
                    http_status=status_code,
                    status_provere="NIJE MOGUĆE PROVERITI",
                    link_status="NIJE PROVERENO",
                    napomena=(
                        f"Neočekivan HTTP status {status_code}. "
                        "Provera nije izvršena kao uspešna."
                    )
                )
            )

            return rows

        # =================================================
        # CONTENT TYPE
        # =================================================

        content_type = (
            response.headers
            .get("Content-Type", "")
            .lower()
        )

        if (
            content_type
            and "text/html" not in content_type
            and "application/xhtml+xml" not in content_type
        ):

            rows.append(
                create_status_row(
                    source_url=source_url,
                    http_status=status_code,
                    status_provere="NIJE MOGUĆE PROVERITI",
                    link_status="NIJE PROVERENO",
                    napomena=(
                        f"URL je dostupan, ali Content-Type je "
                        f"'{content_type}'. Nije potvrđeno da je "
                        f"u pitanju HTML stranica."
                    )
                )
            )

            return rows

        # =================================================
        # HTML
        # =================================================

        html = response.text

        if not html or not html.strip():

            rows.append(
                create_status_row(
                    source_url=source_url,
                    http_status=status_code,
                    status_provere="NIJE MOGUĆE PROVERITI",
                    link_status="NIJE PROVERENO",
                    napomena=(
                        "Server je odgovorio, ali nije vraćen "
                        "HTML sadržaj koji je moguće analizirati."
                    )
                )
            )

            return rows

        # =================================================
        # PARSE HTML
        # =================================================

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        found_links = []

        # =================================================
        # FIND ALL <a href>
        # =================================================

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = (
                link.get("href", "")
                .strip()
            )

            if not href:
                continue

            href_lower = href.lower()

            # Ignore non-web links
            if href_lower.startswith((
                "mailto:",
                "tel:",
                "javascript:",
                "data:"
            )):
                continue

            # Ignore page fragments
            if href.startswith("#"):
                continue

            # Resolve relative URLs
            absolute_href = urljoin(
                final_source_url,
                href
            )

            parsed_href = urlparse(
                absolute_href
            )

            if parsed_href.scheme not in (
                "http",
                "https"
            ):
                continue

            # =================================================
            # TARGET DOMAIN MATCH
            # =================================================

            if not is_target_domain(
                absolute_href,
                target_domain
            ):
                continue

            # =================================================
            # ANCHOR
            # =================================================

            anchor = get_anchor_text(
                link
            )

            # =================================================
            # REL
            # =================================================

            rel_values = get_rel_values(
                link
            )

            rel_attribute = (
                " ".join(rel_values)
                if rel_values
                else ""
            )

            nofollow = (
                "DA"
                if "nofollow" in rel_values
                else "NE"
            )

            sponsored = (
                "DA"
                if "sponsored" in rel_values
                else "NE"
            )

            ugc = (
                "DA"
                if "ugc" in rel_values
                else "NE"
            )

            link_type = get_link_type(
                rel_values
            )

            # =================================================
            # SAVE BACKLINK
            # =================================================

            found_links.append(
                {
                    "Source URL": source_url,
                    "HTTP Status": status_code,
                    "Status provere": "USPEŠNO PROVERENO",
                    "Link ka target domenu": "DA",
                    "Anchor tekst": anchor,
                    "Linkovani target URL": absolute_href,
                    "Rel atribut": rel_attribute,
                    "Nofollow": nofollow,
                    "Sponsored": sponsored,
                    "UGC": ugc,
                    "Link Type": link_type,
                    "Napomena": "",
                }
            )

        # =================================================
        # BACKLINK FOUND
        # =================================================

        if found_links:

            rows.extend(
                found_links
            )

            return rows

        # =================================================
        # BACKLINK NOT FOUND
        # =================================================

        rows.append(
            create_status_row(
                source_url=source_url,
                http_status=status_code,
                status_provere="USPEŠNO PROVERENO",
                link_status="NE",
                napomena=(
                    "Stranica je uspešno otvorena i analizirana, "
                    "ali link ka target domenu nije pronađen "
                    "u dobijenom HTML-u."
                )
            )
        )

        return rows

    # =====================================================
    # TIMEOUT
    # =====================================================

    except requests.exceptions.Timeout:

        rows.append(
            create_status_row(
                source_url=source_url,
                http_status="TIMEOUT",
                status_provere="NIJE MOGUĆE PROVERITI",
                link_status="NIJE PROVERENO",
                napomena=(
                    "Request je istekao pre nego što je stranica "
                    "mogla pouzdano da se proveri."
                )
            )
        )

        return rows

    # =====================================================
    # SSL ERROR
    # =====================================================

    except requests.exceptions.SSLError as e:

        rows.append(
            create_status_row(
                source_url=source_url,
                http_status="SSL ERROR",
                status_provere="NIJE MOGUĆE PROVERITI",
                link_status="NIJE PROVERENO",
                napomena=f"SSL greška: {str(e)}"
            )
        )

        return rows

    # =====================================================
    # CONNECTION ERROR
    # =====================================================

    except requests.exceptions.ConnectionError as e:

        rows.append(
            create_status_row(
                source_url=source_url,
                http_status="CONNECTION ERROR",
                status_provere="NIJE MOGUĆE PROVERITI",
                link_status="NIJE PROVERENO",
                napomena=f"Connection error: {str(e)}"
            )
        )

        return rows

    # =====================================================
    # REQUEST ERROR
    # =====================================================

    except requests.exceptions.RequestException as e:

        rows.append(
            create_status_row(
                source_url=source_url,
                http_status="REQUEST ERROR",
                status_provere="NIJE MOGUĆE PROVERITI",
                link_status="NIJE PROVERENO",
                napomena=f"Request error: {str(e)}"
            )
        )

        return rows

    # =====================================================
    # OTHER ERROR
    # =====================================================

    except Exception as e:

        rows.append(
            create_status_row(
                source_url=source_url,
                http_status="ERROR",
                status_provere="NIJE MOGUĆE PROVERITI",
                link_status="NIJE PROVERENO",
                napomena=f"Neočekivana greška: {str(e)}"
            )
        )

        return rows


# =========================================================
# INPUT
# =========================================================

st.subheader("1. Lista URL-ova")

urls_input = st.text_area(
    "Unesi URL-ove — jedan URL po redu",
    height=300,
    placeholder=(
        "https://example.com/article-1/\n"
        "https://example.org/article-2/\n"
        "https://example.net/article-3/"
    )
)


st.subheader("2. Target domen")

target_input = st.text_input(
    "Unesi target domen",
    placeholder="balkanbet.rs",
    help=(
        "Možeš uneti balkanbet.rs, "
        "www.balkanbet.rs ili https://balkanbet.rs/. "
        "www i target subdomeni se prepoznaju automatski."
    )
)


# =========================================================
# RUN
# =========================================================

if st.button(
    "Run Backlink Check",
    type="primary"
):

    # =====================================================
    # CLEAN URL LIST
    # =====================================================

    urls = [
        line.strip()
        for line in urls_input.splitlines()
        if line.strip()
    ]

    # Remove duplicates while preserving order
    urls = list(
        dict.fromkeys(urls)
    )

    target_domain = normalize_domain(
        target_input
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if not urls:

        st.warning(
            "Unesi najmanje jedan URL."
        )

        st.stop()

    if not target_domain:

        st.warning(
            "Unesi ispravan target domen."
        )

        st.stop()

    # =====================================================
    # INFO
    # =====================================================

    st.info(
        f"Proveravamo {len(urls)} URL-ova "
        f"za linkove ka domenu: {target_domain}"
    )

    # =====================================================
    # RUN CHECKS
    # =====================================================

    results = []

    progress = st.progress(0)

    status_placeholder = st.empty()

    total = len(urls)

    for index, url in enumerate(urls):

        status_placeholder.write(
            f"Checking {index + 1} / {total}: {url}"
        )

        url_results = check_url(
            url,
            target_domain
        )

        results.extend(
            url_results
        )

        progress.progress(
            (index + 1) / total
        )

    status_placeholder.empty()

    # =====================================================
    # DATAFRAME
    # =====================================================

    result_df = pd.DataFrame(
        results,
        columns=RESULT_COLUMNS
    )

    # =====================================================
    # SUMMARY
    # =====================================================

    checked_urls = len(urls)

    urls_with_link = (
        result_df[
            result_df[
                "Link ka target domenu"
            ] == "DA"
        ]["Source URL"]
        .nunique()
    )

    urls_without_link = (
        result_df[
            result_df[
                "Link ka target domenu"
            ] == "NE"
        ]["Source URL"]
        .nunique()
    )

    could_not_check = (
        result_df[
            result_df[
                "Link ka target domenu"
            ] == "NIJE PROVERENO"
        ]["Source URL"]
        .nunique()
    )

    total_backlinks = len(
        result_df[
            result_df[
                "Link ka target domenu"
            ] == "DA"
        ]
    )

    nofollow_links = len(
        result_df[
            result_df[
                "Nofollow"
            ] == "DA"
        ]
    )

    sponsored_links = len(
        result_df[
            result_df[
                "Sponsored"
            ] == "DA"
        ]
    )

    # =====================================================
    # SUMMARY DISPLAY
    # =====================================================

    st.subheader("Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Checked URLs",
        checked_urls
    )

    col2.metric(
        "Link found",
        urls_with_link
    )

    col3.metric(
        "Link not found",
        urls_without_link
    )

    col4.metric(
        "Could not check",
        could_not_check
    )

    col5, col6, col7 = st.columns(3)

    col5.metric(
        "Total backlinks found",
        total_backlinks
    )

    col6.metric(
        "Nofollow backlinks",
        nofollow_links
    )

    col7.metric(
        "Sponsored backlinks",
        sponsored_links
    )

    # =====================================================
    # WARNING
    # =====================================================

    if could_not_check > 0:

        st.warning(
            f"{could_not_check} URL-ova nije bilo moguće pouzdano "
            f"proveriti. Oni se NE računaju kao stranice bez backlinka."
        )

    # =====================================================
    # COLORS
    # =====================================================

    def color_link_status(value):

        if value == "DA":

            return (
                "background-color: #d9ead3; "
                "color: #274e13; "
                "font-weight: 600;"
            )

        if value == "NE":

            return (
                "background-color: #f4cccc; "
                "color: #990000; "
                "font-weight: 600;"
            )

        if value == "NIJE PROVERENO":

            return (
                "background-color: #fce5cd; "
                "color: #783f04; "
                "font-weight: 600;"
            )

        return ""


    def color_check_status(value):

        if value == "USPEŠNO PROVERENO":

            return (
                "background-color: #d9ead3; "
                "color: #274e13;"
            )

        if value == "NIJE MOGUĆE PROVERITI":

            return (
                "background-color: #fce5cd; "
                "color: #783f04; "
                "font-weight: 600;"
            )

        return ""


    def color_rel_status(value):

        if value == "DA":

            return (
                "background-color: #f4cccc; "
                "color: #990000; "
                "font-weight: 600;"
            )

        if value == "NE":

            return (
                "background-color: #d9ead3; "
                "color: #274e13;"
            )

        return ""


    # =====================================================
    # STYLE
    # =====================================================

    styled_df = (
        result_df.style
        .map(
            color_link_status,
            subset=[
                "Link ka target domenu"
            ]
        )
        .map(
            color_check_status,
            subset=[
                "Status provere"
            ]
        )
        .map(
            color_rel_status,
            subset=[
                "Nofollow",
                "Sponsored"
            ]
        )
    )

    # =====================================================
    # ALL RESULTS
    # =====================================================

    st.subheader("Results")

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        height=650,
        column_config={
            "Source URL":
                st.column_config.LinkColumn(
                    "Source URL"
                ),

            "Linkovani target URL":
                st.column_config.LinkColumn(
                    "Linkovani target URL"
                )
        }
    )

    # =====================================================
    # LINKS FOUND
    # =====================================================

    links_found_df = result_df[
        result_df[
            "Link ka target domenu"
        ] == "DA"
    ].copy()

    st.subheader("Links Found")

    if links_found_df.empty:

        st.info(
            "Nije pronađen nijedan potvrđen link "
            "ka target domenu."
        )

    else:

        links_found_display = links_found_df[
            [
                "Source URL",
                "Anchor tekst",
                "Linkovani target URL",
                "Rel atribut",
                "Nofollow",
                "Sponsored",
                "UGC",
                "Link Type"
            ]
        ]

        links_found_styled = (
            links_found_display.style
            .map(
                color_rel_status,
                subset=[
                    "Nofollow",
                    "Sponsored"
                ]
            )
        )

        st.dataframe(
            links_found_styled,
            use_container_width=True,
            hide_index=True,
            height=500,
            column_config={
                "Source URL":
                    st.column_config.LinkColumn(
                        "Source URL"
                    ),

                "Linkovani target URL":
                    st.column_config.LinkColumn(
                        "Linkovani target URL"
                    )
            }
        )

    # =====================================================
    # COULD NOT CHECK
    # =====================================================

    failed_df = result_df[
        result_df[
            "Link ka target domenu"
        ] == "NIJE PROVERENO"
    ].copy()

    if not failed_df.empty:

        st.subheader(
            "⚠️ URLs koje nije moguće proveriti"
        )

        st.dataframe(
            failed_df[
                [
                    "Source URL",
                    "HTTP Status",
                    "Napomena"
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Source URL":
                    st.column_config.LinkColumn(
                        "Source URL"
                    )
            }
        )

    # =====================================================
    # CSV EXPORT
    # =====================================================

    csv = (
        result_df
        .to_csv(
            index=False
        )
        .encode("utf-8-sig")
    )

    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="bulk_backlink_check.csv",
        mime="text/csv"
    )
