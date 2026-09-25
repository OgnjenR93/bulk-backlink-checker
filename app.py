import streamlit as st
import requests
import pandas as pd

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


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
    "Alat prvo pokušava standardnu HTTP proveru. Ako pristup nije moguć, "
    "automatski pokušava da otvori stranicu kroz Chromium browser."
)


# =========================================================
# SETTINGS
# =========================================================

REQUEST_TIMEOUT = 25
BROWSER_TIMEOUT = 30000

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


RESULT_COLUMNS = [
    "Source URL",
    "HTTP Status",
    "Status provere",
    "Metod provere",
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
# DOMAIN FUNCTIONS
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


def is_target_domain(href, target_domain):

    link_domain = get_link_domain(href)

    if not link_domain:
        return False

    if link_domain == target_domain:
        return True

    if link_domain.endswith("." + target_domain):
        return True

    return False


# =========================================================
# LINK FUNCTIONS
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

    return list(dict.fromkeys(values))


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


def get_anchor_text(link):

    anchor = link.get_text(
        " ",
        strip=True
    )

    if anchor:
        return anchor

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
    method="",
    link_status="",
    napomena=""
):

    return {
        "Source URL": source_url,
        "HTTP Status": http_status,
        "Status provere": status_provere,
        "Metod provere": method,
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
# ANALYZE HTML
# =========================================================

def analyze_html(
    html,
    source_url,
    base_url,
    target_domain,
    http_status,
    method
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    found_links = []

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

        if href_lower.startswith((
            "mailto:",
            "tel:",
            "javascript:",
            "data:"
        )):
            continue

        if href.startswith("#"):
            continue

        absolute_href = urljoin(
            base_url,
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

        if not is_target_domain(
            absolute_href,
            target_domain
        ):
            continue

        anchor = get_anchor_text(
            link
        )

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

        found_links.append(
            {
                "Source URL": source_url,
                "HTTP Status": http_status,
                "Status provere": "USPEŠNO PROVERENO",
                "Metod provere": method,
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

    if found_links:
        return found_links

    return [
        create_status_row(
            source_url=source_url,
            http_status=http_status,
            status_provere="USPEŠNO PROVERENO",
            method=method,
            link_status="NE",
            napomena=(
                "Stranica je uspešno otvorena i analizirana, "
                "ali link ka target domenu nije pronađen."
            )
        )
    ]


# =========================================================
# REQUESTS CHECK
# =========================================================

def try_requests(
    source_url,
    target_domain
):

    try:

        response = requests.get(
            source_url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        status_code = response.status_code
        final_url = response.url

        # ---------------------------------------------
        # HTTP ERROR -> browser fallback
        # ---------------------------------------------

        if status_code >= 400:
            return None, status_code

        # ---------------------------------------------
        # INVALID RESPONSE
        # ---------------------------------------------

        html = response.text

        if not html or not html.strip():
            return None, status_code

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
            return None, status_code

        # ---------------------------------------------
        # SUCCESS
        # ---------------------------------------------

        rows = analyze_html(
            html=html,
            source_url=source_url,
            base_url=final_url,
            target_domain=target_domain,
            http_status=status_code,
            method="Requests"
        )

        return rows, status_code

    except requests.exceptions.RequestException:

        return None, "REQUEST ERROR"

    except Exception:

        return None, "ERROR"


# =========================================================
# BROWSER FALLBACK
# =========================================================

def try_browser(
    source_url,
    target_domain,
    original_status
):

    browser = None

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )

            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="sr-RS",
                ignore_https_errors=True
            )

            page = context.new_page()

            response = page.goto(
                source_url,
                wait_until="domcontentloaded",
                timeout=BROWSER_TIMEOUT
            )

            # Give JS a little time to modify the DOM
            page.wait_for_timeout(1500)

            browser_status = ""

            if response:
                browser_status = response.status

            final_url = page.url

            html = page.content()

            if not html or not html.strip():

                browser.close()

                return [
                    create_status_row(
                        source_url=source_url,
                        http_status=(
                            browser_status
                            or original_status
                        ),
                        status_provere="NIJE MOGUĆE PROVERITI",
                        method="Browser fallback",
                        link_status="NIJE PROVERENO",
                        napomena=(
                            "Browser je otvoren, ali nije dobijen "
                            "HTML sadržaj za pouzdanu proveru."
                        )
                    )
                ]

            # If browser still gets an actual HTTP error,
            # do not call it a successful check.
            if (
                browser_status
                and browser_status >= 400
            ):

                browser.close()

                return [
                    create_status_row(
                        source_url=source_url,
                        http_status=browser_status,
                        status_provere="NIJE MOGUĆE PROVERITI",
                        method="Browser fallback",
                        link_status="NIJE PROVERENO",
                        napomena=(
                            f"Requests je vratio {original_status}, "
                            f"a Chromium HTTP {browser_status}. "
                            f"Stranicu nije moguće pouzdano proveriti."
                        )
                    )
                ]

            rows = analyze_html(
                html=html,
                source_url=source_url,
                base_url=final_url,
                target_domain=target_domain,
                http_status=(
                    browser_status
                    if browser_status
                    else original_status
                ),
                method="Browser"
            )

            browser.close()

            return rows

    except PlaywrightTimeoutError:

        if browser:
            try:
                browser.close()
            except Exception:
                pass

        return [
            create_status_row(
                source_url=source_url,
                http_status=original_status,
                status_provere="NIJE MOGUĆE PROVERITI",
                method="Browser fallback",
                link_status="NIJE PROVERENO",
                napomena=(
                    "Standardni request nije uspeo, a Chromium "
                    "je istekao pre nego što je stranica mogla "
                    "da se proveri."
                )
            )
        ]

    except Exception as e:

        if browser:
            try:
                browser.close()
            except Exception:
                pass

        return [
            create_status_row(
                source_url=source_url,
                http_status=original_status,
                status_provere="NIJE MOGUĆE PROVERITI",
                method="Browser fallback",
                link_status="NIJE PROVERENO",
                napomena=(
                    f"Browser fallback nije uspeo: {str(e)}"
                )
            )
        ]


# =========================================================
# MAIN URL CHECK
# =========================================================

def check_url(
    source_url,
    target_domain
):

    # ---------------------------------------------
    # FIRST: REQUESTS
    # ---------------------------------------------

    request_result, request_status = try_requests(
        source_url,
        target_domain
    )

    if request_result is not None:
        return request_result

    # ---------------------------------------------
    # SECOND: CHROMIUM
    # ---------------------------------------------

    return try_browser(
        source_url,
        target_domain,
        request_status
    )


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
        "www.balkanbet.rs ili https://balkanbet.rs/."
    )
)


# =========================================================
# RUN
# =========================================================

if st.button(
    "Run Backlink Check",
    type="primary"
):

    urls = [
        line.strip()
        for line in urls_input.splitlines()
        if line.strip()
    ]

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
    # RUN
    # =====================================================

    st.info(
        f"Proveravamo {len(urls)} URL-ova "
        f"za linkove ka domenu: {target_domain}"
    )

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

    browser_urls = (
        result_df[
            result_df[
                "Metod provere"
            ] == "Browser"
        ]["Source URL"]
        .nunique()
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

    col5, col6, col7, col8 = st.columns(4)

    col5.metric(
        "Total backlinks",
        total_backlinks
    )

    col6.metric(
        "Nofollow",
        nofollow_links
    )

    col7.metric(
        "Sponsored",
        sponsored_links
    )

    col8.metric(
        "Browser fallback",
        browser_urls
    )

    # =====================================================
    # WARNING
    # =====================================================

    if could_not_check > 0:

        st.warning(
            f"{could_not_check} URL-ova nije bilo moguće pouzdano "
            f"proveriti ni nakon browser fallback provere."
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
            subset=["Link ka target domenu"]
        )
        .map(
            color_check_status,
            subset=["Status provere"]
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
    # RESULTS
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
            "Nije pronađen nijedan potvrđen "
            "link ka target domenu."
        )

    else:

        links_found_display = links_found_df[
            [
                "Source URL",
                "Metod provere",
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
                    "Metod provere",
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
