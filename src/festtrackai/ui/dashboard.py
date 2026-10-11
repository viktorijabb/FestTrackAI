import streamlit as st
import pandas as pd
from festtrackai.db.database import init_db, get_all_festivals, update_festival_status, insert_festival
from festtrackai.scraper.crawler import fetch_filmfreeway_festivals

init_db()

st.set_page_config(
    page_title="FestTrackAI Dashboard",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 FestTrackAI - Film Festival Tracker")
st.markdown("Monitor submission deadlines and track affordable film festivals effortlessly.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Filter Controls")

festivals = get_all_festivals()
df = pd.DataFrame(festivals) if festivals else pd.DataFrame(columns=["fee"])

min_fee = float(df["fee"].min()) if not df.empty else 0.0
max_fee_avail = float(df["fee"].max()) if not df.empty else 50.0

max_fee_filter = st.sidebar.slider(
    "Max Submission Fee ($)",
    min_value=min_fee,
    max_value=max_fee_avail,
    value=10.0
)

# FilmFreeway Scraper Trigger in Sidebar
st.sidebar.markdown("---")
st.sidebar.header("Data Sync")

if st.sidebar.button("🌐 Scrape FilmFreeway", type="secondary"):
    with st.spinner("Scraping live data from FilmFreeway..."):
        try:
            scraped_items = fetch_filmfreeway_festivals()
            if scraped_items:
                for item in scraped_items:
                    insert_festival(item.model_dump())
                st.sidebar.success(f"Successfully scraped {len(scraped_items)} festivals!")
                st.rerun()
            else:
                st.sidebar.warning("No festival cards found on the page.")
        except Exception as e:
            st.sidebar.error(f"Scraper error: {e}")

# --- MAIN DASHBOARD CONTENT ---
if not festivals:
    st.warning("No festivals found in the database yet. Click 'Scrape FilmFreeway' in the sidebar or run your seed script to get started!")
else:
    filtered_df = df[df["fee"] <= max_fee_filter]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Festivals Tracked", len(df))
    col2.metric("Matching Filter", len(filtered_df))
    col3.metric("Budget Threshold", f"${max_fee_filter:.2f}")

    st.markdown("---")

    st.subheader("Festival Directory")
    st.markdown("Double-click the **Application Status** column to change a status, then click **Save Status Changes** below.")

    edited_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": "ID",
            "name": "Festival Name",
            "fee": st.column_config.NumberColumn("Fee ($)", format="$%.2f"),
            "tier_deadline": "Tier / Early Deadline",
            "absolute_deadline": "Absolute Final Deadline",
            "status": st.column_config.SelectboxColumn(
                "Application Status",
                options=["Unapplied", "Applied"],
                required=True
            )
        },
        key="festival_editor"
    )

    if st.button("💾 Save Status Changes", type="primary"):
        for _, row in edited_df.iterrows():
            update_festival_status(row["id"], row["status"])
        st.success("Application statuses updated successfully!")
        st.rerun()