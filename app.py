import streamlit as st
import requests
import pandas as pd

from bs4 import BeautifulSoup
from urllib.parse import urlparse


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
    "kroz koji anchor tekst i ka kom URL-u target domena link vodi."
)


# =========================================================
# SETTINGS
# =========================================================

REQUEST_TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)


# =========================================================
# NORMALIZE DOMAIN
# =========================================================

def normalize_domain(value):

    value = str(value).strip().lower()

    if not value:
        return ""

    if not value.startswith(
        ("http://", "https://")
    ):
        value = "https://" + value

    parsed = urlparse(value)

    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


# =========================================================
# GET LINK DOMAIN
# =========================================================

def get_link_domain(url):

    try:

        parsed = urlparse(
            url
        )

        domain = (
            parsed.netloc
            .lower()
        )

        if domain.startswith(
            "www."
        ):
            domain = domain[4:]

        return domain

    except Exception:

        return ""


# =========================================================
# CHECK IF LINK BELONGS TO TARGET DOMAIN
# =========================================================

def is_target_domain(
    href,
    target_domain
):

    link_domain = (
        get_link_domain(
            href
        )
    )

    if not link_domain:
        return False

    # Exact domain
    if (
        link_domain
        == target_domain
    ):
        return True

    # Subdomain
    if link_domain.endswith(
        "." + target_domain
    ):
        return True

    return False


# =========================================================
# LINK TYPE
# =========================================================

def get_link_type(link):

    rel = link.get(
        "rel",
        []
    )

    if isinstance(rel, str):

        rel_values = (
            rel.lower()
            .split()
        )

    else:

        rel_values = [
            str(value).lower()
            for value in rel
        ]

    types = []

    if "nofollow" in rel_values:
        types.append("NOFOLLOW")

    if "sponsored" in rel_values:
        types.append("SPONSORED")

    if "ugc" in rel_values:
        types.append("UGC")

    if not types:
        return "FOLLOW"

    return " + ".join(
        types
    )


# =========================================================
# CHECK SOURCE URL
# =========================================================

def check_url(
    source_url,
    target_domain
):

    rows = []

    try:

        response = requests.get(
            source_url,
            headers={
                "User-Agent": USER_AGENT
            },
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        status_code = (
            response.status_code
        )

        final_source_url = (
            response.url
        )

        # We still parse HTML if possible
        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        found_links = []

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = (
                link.get(
                    "href",
                    ""
                )
                .strip()
            )

            if not href:
                continue

            if is_target_domain(
                href,
                target_domain
            ):

                anchor = (
                    link.get_text(
                        " ",
                        strip=True
                    )
                )

                if not anchor:

                    # Image link / empty anchor
                    image = link.find(
                        "img"
                    )

                    if image:

                        alt = image.get(
                            "alt",
                            ""
                        ).strip()

                        if alt:
                            anchor = (
                                f"[IMAGE: {alt}]"
                            )
                        else:
                            anchor = (
                                "[IMAGE LINK]"
                            )

                    else:

                        anchor = (
                            "[EMPTY ANCHOR]"
                        )

                link_type = (
                    get_link_type(
                        link
                    )
                )

                found_links.append(
                    {
                        "Anchor tekst":
                            anchor,

                        "Linkovani target URL":
                            href,

                        "Link Type":
                            link_type
                    }
                )

        # =============================================
        # TARGET LINKS FOUND
        # =============================================

        if found_links:

            for item in found_links:

                rows.append(
                    {
                        "Source URL":
                            source_url,

                        "HTTP Status":
                            status_code,

                        "Final Source URL":
                            final_source_url,

                        "Link ka target domenu":
                            "DA",

                        "Anchor tekst":
                            item[
                                "Anchor tekst"
                            ],

                        "Linkovani target URL":
                            item[
                                "Linkovani target URL"
                            ],

                        "Link Type":
                            item[
                                "Link Type"
                            ],

                        "Error":
                            ""
                    }
                )

        # =============================================
        # NO TARGET LINKS
        # =============================================

        else:

            rows.append(
                {
                    "Source URL":
                        source_url,

                    "HTTP Status":
                        status_code,

                    "Final Source URL":
                        final_source_url,

                    "Link ka target domenu":
                        "NE",

                    "Anchor tekst":
                        "",

                    "Linkovani target URL":
                        "",

                    "Link Type":
                        "",

                    "Error":
                        ""
                }
            )

    except Exception as e:

        rows.append(
            {
                "Source URL":
                    source_url,

                "HTTP Status":
                    "ERROR",

                "Final Source URL":
                    "",

                "Link ka target domenu":
                    "ERROR",

                "Anchor tekst":
                    "",

                "Linkovani target URL":
                    "",

                "Link Type":
                    "",

                "Error":
                    str(e)
            }
        )

    return rows


# =========================================================
# INPUT
# =========================================================

st.subheader(
    "1. Lista URL-ova"
)

urls_input = st.text_area(
    "Unesi URL-ove — jedan URL po redu",
    height=300,
    placeholder=(
        "https://example.com/article-1/\n"
        "https://example.org/article-2/\n"
        "https://example.net/article-3/"
    )
)


st.subheader(
    "2. Target domen"
)

target_input = st.text_input(
    "Unesi target domen",
    placeholder="ananas.rs",
    help=(
        "Možeš uneti ananas.rs, "
        "www.ananas.rs ili https://ananas.rs/"
    )
)


# =========================================================
# RUN
# =========================================================

if st.button(
    "Run Backlink Check",
    type="primary"
):

    # =============================================
    # CLEAN URL LIST
    # =============================================

    urls = [
        line.strip()
        for line in urls_input.splitlines()
        if line.strip()
    ]

    # Remove duplicates
    urls = list(
        dict.fromkeys(
            urls
        )
    )

    target_domain = (
        normalize_domain(
            target_input
        )
    )

    # =============================================
    # VALIDATION
    # =============================================

    if not urls:

        st.warning(
            "Unesi najmanje jedan URL."
        )

        st.stop()

    if not target_domain:

        st.warning(
            "Unesi target domen."
        )

        st.stop()

    # =============================================
    # INFO
    # =============================================

    st.info(
        f"Proveravamo {len(urls)} URL-ova "
        f"za linkove ka domenu: {target_domain}"
    )

    # =============================================
    # RUN CHECKS
    # =============================================

    results = []

    progress = st.progress(
        0
    )

    status_placeholder = (
        st.empty()
    )

    total = len(
        urls
    )

    for index, url in enumerate(
        urls
    ):

        status_placeholder.write(
            f"Checking "
            f"{index + 1} / "
            f"{total}: "
            f"{url}"
        )

        url_results = (
            check_url(
                url,
                target_domain
            )
        )

        results.extend(
            url_results
        )

        progress.progress(
            (index + 1)
            / total
        )

    status_placeholder.empty()

    # =============================================
    # DATAFRAME
    # =============================================

    result_df = pd.DataFrame(
        results
    )

    # =============================================
    # SUMMARY
    # =============================================

    checked_urls = len(
        urls
    )

    urls_with_link = (
        result_df[
            result_df[
                "Link ka target domenu"
            ]
            == "DA"
        ][
            "Source URL"
        ]
        .nunique()
    )

    urls_without_link = (
        result_df[
            result_df[
                "Link ka target domenu"
            ]
            == "NE"
        ][
            "Source URL"
        ]
        .nunique()
    )

    error_urls = (
        result_df[
            result_df[
                "Link ka target domenu"
            ]
            == "ERROR"
        ][
            "Source URL"
        ]
        .nunique()
    )

    st.subheader(
        "Summary"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

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
        "Errors",
        error_urls
    )

    # =============================================
    # STYLE
    # =============================================

    def color_link_status(
        value
    ):

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

        if value == "ERROR":

            return (
                "background-color: #fce5cd; "
                "color: #783f04; "
                "font-weight: 600;"
            )

        return ""


    styled_df = (
        result_df.style
        .map(
            color_link_status,
            subset=[
                "Link ka target domenu"
            ]
        )
    )

    # =============================================
    # RESULTS
    # =============================================

    st.subheader(
        "Results"
    )

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

            "Final Source URL":
                st.column_config.LinkColumn(
                    "Final Source URL"
                ),

            "Linkovani target URL":
                st.column_config.LinkColumn(
                    "Linkovani target URL"
                )
        }
    )

    # =============================================
    # LINKS FOUND ONLY
    # =============================================

    links_found_df = result_df[
        result_df[
            "Link ka target domenu"
        ]
        == "DA"
    ].copy()

    st.subheader(
        "Links Found"
    )

    if links_found_df.empty:

        st.warning(
            "Nije pronađen nijedan link ka target domenu."
        )

    else:

        st.dataframe(
            links_found_df[
                [
                    "Source URL",
                    "Anchor tekst",
                    "Linkovani target URL",
                    "Link Type"
                ]
            ],
            use_container_width=True,
            hide_index=True,
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

    # =============================================
    # CSV EXPORT
    # =============================================

    csv = (
        result_df
        .to_csv(
            index=False
        )
        .encode(
            "utf-8-sig"
        )
    )

    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=(
            "bulk_backlink_check.csv"
        ),
        mime="text/csv"
    )
