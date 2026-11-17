import sqlite3
import pandas as pd
import streamlit as st
from festtrackai.db.database import init_db

def load_festival_data():
    # Connect to the local SQLite database mapped in Docker
    conn = sqlite3.connect("festivals.db")

    # Query all saved festival submissions
    df = pd.read_sql("SELECT * FROM festivals ORDER BY id DESC", conn)
    conn.close()
    return df

init_db()
st.title("FestTrackAI Dashboard")
st.caption("Unknown fees are blank; TBD deadlines have not been extracted. Existing legacy values are retained.")
df_festivals = load_festival_data()

if not df_festivals.empty:
    st.dataframe(df_festivals)
else:
    st.info("No festival records found yet.")
