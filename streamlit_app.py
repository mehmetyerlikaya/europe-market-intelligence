"""Local presentation interface for the existing market intelligence pipeline."""

import threading

import pandas as pd
import streamlit as st

from src.presentation import project_config, read_snapshot, refresh

st.set_page_config(page_title="European Market Intelligence", page_icon="🌍", layout="wide")


@st.cache_resource
def run_lock():
    return threading.Lock()


def main():
    config = project_config()
    st.sidebar.title("Market intelligence")
    st.sidebar.caption("LOCAL DATA WORKSPACE")
    st.sidebar.write("Public European data, made consistent and reusable.")
    st.sidebar.divider()
    st.sidebar.markdown("**How to present this project**")
    st.sidebar.write(
        "1. Explain the flow.\n2. Run a refresh.\n"
        "3. Explore a market.\n4. Inspect quality and sources."
    )
    st.sidebar.divider()
    st.sidebar.caption("Runs on your computer. No account or API key required.")

    st.caption("EUROPE / MARKET DATA PIPELINE")
    st.title("From public data to market context")
    st.write(
        "Population, demographics, economic context and holidays — one trusted row per market."
    )

    action, note = st.columns([1, 3])
    clicked = action.button("Run pipeline", type="primary", width="stretch")
    note.caption(
        "Fetch live public sources, rebuild the local snapshot, and validate before publishing."
    )
    if clicked:
        lock = run_lock()
        if not lock.acquire(blocking=False):
            st.warning("Another browser session is already refreshing. Try again when it finishes.")
        else:
            try:
                with st.status("Refreshing the pipeline…", expanded=True) as status:
                    messages = []
                    log = st.empty()

                    def show_line(line):
                        messages.append(line)
                        log.code("\n".join(messages), language="text")

                    code = refresh(show_line)
                    st.session_state["run_log"] = messages
                    st.session_state["run_ok"] = code == 0
                    status.update(
                        label="Refresh complete" if code == 0 else "Refresh failed — see log",
                        state="complete" if code == 0 else "error",
                        expanded=code != 0,
                    )
            except Exception as exc:
                st.session_state["run_ok"] = False
                st.error(f"Unable to run the pipeline: {exc}")
            finally:
                lock.release()
    if st.session_state.get("run_ok") is False:
        st.warning(
            "The latest refresh failed. Any table below is the saved database snapshot; "
            "check its load time."
        )
    if "run_log" in st.session_state:
        with st.expander("Latest refresh log"):
            st.code("\n".join(st.session_state["run_log"]), language="text")

    try:
        snapshot = read_snapshot(config)
    except Exception as exc:
        st.error(f"Cannot read the local database: {exc}")
        st.info(
            "If a separate terminal is refreshing the pipeline, wait for it to finish, then reload."
        )
        return
    if snapshot is None:
        st.info("No saved snapshot yet. Click Run pipeline to fetch data and create the first one.")
        return
    frame = snapshot["markets"]
    if frame.empty:
        st.error("The saved mart is empty. Run the pipeline to rebuild it.")
        return
    quality_error = snapshot["quality_error"]
    first = frame.iloc[0]
    cards = st.columns(4)
    cards[0].metric("Markets", len(frame))
    cards[1].metric("Countries", frame["country_code"].nunique())
    cards[2].metric("Source datasets", "4")
    cards[3].metric("Saved snapshot checks", "Passed" if quality_error is None else "Failed")
    st.caption(
        f"Last loaded: {first['loaded_at_utc']} UTC · Calendar as of {first['as_of_date'].date()}"
    )
    st.info(
        f"Source years: population {first['population_reference_year']} · "
        f"density {first['density_reference_year']} · GDP {first['gdp_reference_year']}. "
        "The demo keeps GDP's older year explicit because complete 2024 coverage was unavailable. "
        "Refreshing does not change the configured calendar date."
    )

    overview, explorer, quality = st.tabs(
        ["Pipeline overview", "Market explorer", "Quality & sources"]
    )
    with overview:
        st.subheader("One repeatable path from source to output")
        stages = [
            ("01 · FETCH", "Public sources", "Eurostat statistics + national holiday calendars"),
            (
                "02 · RAW",
                "Preserve the source",
                "Normalized records, source URLs and statistical flags",
            ),
            (
                "03 · STAGING",
                "Make it consistent",
                "SQL types, age shares and national-holiday filtering",
            ),
            (
                "04 · MART",
                "One row per market",
                "Join using verified region codes and country identifiers",
            ),
            (
                "05 · VALIDATE",
                "Publish when valid",
                "Check the contract, commit DuckDB and export CSV",
            ),
        ]
        for col, (number, title, detail) in zip(st.columns(5), stages, strict=True):
            with col.container(border=True):
                st.caption(number)
                st.markdown(f"**{title}**")
                st.write(detail)
        st.caption("FETCH → RAW → STAGING → MART → VALIDATE & PUBLISH")
        st.subheader("Inside the saved snapshot")
        st.dataframe(snapshot["layers"], hide_index=True, width="stretch")
        st.write(
            "The final table contains one row per configured market. "
            "Holiday staging counts dates per country; socioeconomic staging counts regions."
        )
        st.markdown("**Why this exists**")
        st.write(
            "Analysts can reuse a consistent dataset instead of rebuilding source mapping "
            "and joins for each analysis. This project supplies context for forecasting, "
            "pricing and planning; it does not predict demand or choose routes."
        )

    with explorer:
        st.subheader("Explore the markets")
        selected = st.multiselect(
            "Markets to display",
            frame["market_name"].tolist(),
            default=frame["market_name"].tolist(),
        )
        filtered = frame[frame["market_name"].isin(selected)]
        columns = [
            "market_name",
            "country_code",
            "population_total",
            "population_density_per_km2",
            "gdp_per_capita_pps",
            "next_public_holiday_date",
            "public_holidays_next_30d",
        ]
        st.dataframe(
            filtered[columns],
            hide_index=True,
            width="stretch",
            column_config={
                "market_name": "Market",
                "country_code": "Country",
                "population_total": st.column_config.NumberColumn("Population", format="localized"),
                "population_density_per_km2": st.column_config.NumberColumn(
                    "People / km²", format="%.1f"
                ),
                "gdp_per_capita_pps": st.column_config.NumberColumn(
                    "GDP / person (PPS)", format="localized"
                ),
                "next_public_holiday_date": st.column_config.DateColumn("Next national holiday"),
                "public_holidays_next_30d": "Holiday dates in 30 days",
            },
        )
        st.download_button(
            "Download displayed markets (CSV)",
            filtered.to_csv(index=False).encode("utf-8"),
            file_name="market_intelligence.csv",
            mime="text/csv",
            disabled=quality_error is not None,
        )
        if selected:
            market = st.selectbox("Inspect a market", selected)
            row = filtered[filtered["market_name"] == market].iloc[0]
            st.caption(f"Statistical region: {row['nuts3_code']} · Market key: {row['market_id']}")
            ages = st.columns(3)
            for col, label, key in zip(
                ages,
                ["Under 15", "Age 15–64", "Age 65+"],
                ["young_share_pct", "working_age_share_pct", "senior_share_pct"],
                strict=True,
            ):
                col.metric(label, f"{row[key]:.1f}%")
            if pd.isna(row["next_public_holiday_date"]):
                st.write("No later national public holiday in the fetched year.")
            else:
                st.write(
                    f"Next holiday: **{row['next_public_holiday_name']}**, "
                    f"{row['next_public_holiday_date'].date()} "
                    f"({int(row['days_until_next_public_holiday'])} days "
                    "after the configured date)."
                )
        with st.expander("Full data contract: all output columns"):
            st.dataframe(filtered, hide_index=True, width="stretch")

    with quality:
        st.subheader("Check the evidence")
        if quality_error is None:
            st.success(
                "The saved snapshot passes the pipeline's mart validator "
                "against the current configuration."
            )
        else:
            st.error(f"Saved snapshot validation failed: {quality_error}")
        st.write(
            "Checks cover market completeness and uniqueness, required fields, configured "
            "identifiers and years, positive finite metrics, age-share ranges and totals, "
            "and calendar consistency and country coverage."
        )
        st.caption(
            "This is a fresh validation of the saved mart. External APIs are contacted "
            "and source parsing checks run only during refresh."
        )
        st.dataframe(
            snapshot["provenance"],
            hide_index=True,
            width="stretch",
            column_config={
                "URL": st.column_config.LinkColumn("Source request"),
            },
        )
        st.markdown(
            "[Holiday API](https://nagerholidays.com/api) · "
            "National public holidays only, for the configured year."
        )
        st.markdown("**Boundaries to explain when presenting**")
        st.write(
            "NUTS 3 is a regional proxy, not always a city boundary. Source years differ. "
            "Holidays exclude today and include day 30; cross-year windows are rejected. "
            "The pipeline keeps one snapshot, and source statistics may be revised."
        )
        st.caption(
            "DuckDB is authoritative. The CSV is replaced after database commit; "
            "a failed CSV replacement is reported in the refresh log."
        )


main()
