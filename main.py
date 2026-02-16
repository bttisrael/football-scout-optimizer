import streamlit as st
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from google.cloud import bigquery
import os
import json
import plotly.graph_objects as go

# --- CONFIGURATION & CLIENT (Keep as is) ---
PROJECT_ID = 'otimizador-cargas'
JSON_KEY_FILE = "otimizador-cargas-79af1f710cb3.json"


def get_bq_client():
    # Se estiver rodando localmente com o arquivo JSON
    if os.path.exists(JSON_KEY_FILE):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(JSON_KEY_FILE)
        return bigquery.Client(project=PROJECT_ID)

    # Se estiver no Streamlit Cloud usando st.secrets
    elif "gcp_service_account" in st.secrets:
        # No Streamlit Cloud, st.secrets["gcp_service_account"] já é um dicionário.
        # Não precisamos de json.loads().
        creds_dict = st.secrets["gcp_service_account"]
        return bigquery.Client.from_service_account_info(creds_dict, project=PROJECT_ID)

    else:
        st.error("Credentials not found.")
        st.stop()


def get_flag(country_name):
    flags = {
        "Brazil": "🇧🇷", "Portugal": "🇵🇹", "Argentina": "🇦🇷", "France": "🇫🇷",
        "Germany": "🇩🇪", "Spain": "🇪🇸", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Italy": "🇮🇹",
        "Netherlands": "🇳🇱", "Poland": "🇵🇱", "Belgium": "🇧🇪", "Uruguay": "🇺🇾",
        "Norway": "🇳🇴", "Croatia": "🇭🇷", "Senegal": "🇸🇳", "Morocco": "🇲🇦"
    }
    return flags.get(str(country_name).strip(), "🏳️")


@st.cache_data
def load_data():
    client = get_bq_client()
    query = f"SELECT * FROM `{PROJECT_ID}.sports.optimization_final_input`"
    return client.query(query).to_dataframe()


# --- COORDINATES ---
coords_map = {
    'Goalkeeper': [[50, 8]],
    'Right-Back': [[85, 28]], 'Left-Back': [[15, 28]], 'Centre-Back': [[35, 23], [65, 23], [50, 23]],
    'Defensive Midfield': [[40, 45], [60, 45]], 'Central Midfield': [[50, 55], [30, 55], [70, 55]],
    'Attacking Midfield': [[50, 68], [30, 68], [70, 68]],
    'Right Winger': [[85, 80]], 'Left Winger': [[15, 80]], 'Centre-Forward': [[50, 92], [35, 92], [65, 92]]
}


def get_pos_color(pos):
    if pos == 'Goalkeeper': return "GhostWhite"
    if 'Back' in pos or 'Centre-Back' in pos: return "#FF4B4B"
    if 'Midfield' in pos: return "#FFD700"
    return "#00D4FF"


def create_pitch_figure(selected_df=None):
    fig = go.Figure()
    # THE FIX: Add the field shapes but set layer='below'
    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=100,
                  fillcolor="#1a4d1a", line_color="white", line_width=2, layer='below')
    fig.add_shape(type="circle", x0=40, y0=42, x1=60, y1=58,
                  line_color="rgba(255,255,255,0.4)", layer='below')
    fig.add_shape(type="line", x0=0, y0=50, x1=100, y1=50,
                  line_color="rgba(255,255,255,0.4)", layer='below')

    if selected_df is not None:
        pos_counter = {}
        for _, p in selected_df.iterrows():
            pos = p['api_pos']
            idx = pos_counter.get(pos, 0)
            if pos in coords_map and idx < len(coords_map[pos]):
                cx, cy = coords_map[pos][idx]
                fig.add_trace(go.Scatter(
                    x=[cx], y=[cy], mode="markers",
                    marker=dict(size=22, color=get_pos_color(pos), line=dict(width=2, color="white")),
                    hoverinfo="skip"
                ))
                fig.add_annotation(
                    x=cx, y=cy + 5,
                    text=f"<b>{p['display_name']}</b>",
                    showarrow=False,
                    font=dict(family="Arial Black", size=13, color="white"),
                    bgcolor="rgba(0,0,0,0.6)",
                    borderpad=3, borderwidth=1, bordercolor="white"
                )
                pos_counter[pos] = idx + 1

    fig.update_layout(showlegend=False, height=550, margin=dict(l=5, r=5, b=5, t=5),
                      xaxis=dict(visible=False, range=[-25, 100]),
                      yaxis=dict(visible=False, range=[-10, 100]),
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    return fig
# --- APP LOGIC ---
st.set_page_config(page_title="Elite Scout Optimizer", layout="wide")
st.title("⚽ Elite Squad Optimizer")

df_raw = load_data()

# Sidebar
st.sidebar.header("Strategy Settings")
budget = st.sidebar.slider("Budget (€M)", 50, 600, 300)
formation = st.sidebar.selectbox("Formation", ["4-3-3", "4-4-2", "3-5-2"])

st.sidebar.header("Attribute Multipliers")
m_attack = st.sidebar.slider("Attack Weight", 0.5, 2.0, 1.0)
m_defense = st.sidebar.slider("Defense Weight", 0.5, 2.0, 1.0)

# Calculate dynamic score using SQL baseline + Multipliers
df_raw['final_score'] = df_raw['performance_score']  # Baseline from your SQL
# If it's a defender, apply defense multiplier, etc.
df_raw.loc[df_raw['api_pos'].str.contains('Back|Centre-Back|Defensive'), 'final_score'] *= m_defense
df_raw.loc[df_raw['api_pos'].str.contains('Forward|Winger|Attacking'), 'final_score'] *= m_attack

col_pitch, col_metrics = st.columns([1, 1])

if st.sidebar.button("Optimize Squad"):
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag', 0)
        env.start()
        with gp.Model("Opt", env=env) as m:
            x = m.addVars(df_raw.index, vtype=GRB.BINARY)
            m.setObjective(gp.quicksum(df_raw.loc[i, 'final_score'] * x[i] for i in df_raw.index), GRB.MAXIMIZE)
            m.addConstr(gp.quicksum(df_raw.loc[i, 'market_value_mio'] * x[i] for i in df_raw.index) <= budget)
            m.addConstr(gp.quicksum(x[i] for i in df_raw.index) == 11)

            pos_req = {
                "4-3-3": {'Goalkeeper': 1, 'Right-Back': 1, 'Left-Back': 1, 'Centre-Back': 2, 'Defensive Midfield': 1,
                          'Central Midfield': 1, 'Attacking Midfield': 1, 'Right Winger': 1, 'Left Winger': 1,
                          'Centre-Forward': 1},
                "4-4-2": {'Goalkeeper': 1, 'Right-Back': 1, 'Left-Back': 1, 'Centre-Back': 2, 'Defensive Midfield': 1,
                          'Central Midfield': 2, 'Right Winger': 1, 'Left Winger': 1, 'Centre-Forward': 1},
                "3-5-2": {'Goalkeeper': 1, 'Centre-Back': 3, 'Defensive Midfield': 2, 'Central Midfield': 1,
                          'Attacking Midfield': 2, 'Centre-Forward': 2}
            }
            for pos, count in pos_req[formation].items():
                m.addConstr(gp.quicksum(x[i] for i in df_raw.index if df_raw.loc[i, 'api_pos'] == pos) == count)

            m.optimize()
            if m.status == GRB.OPTIMAL:
                res = df_raw.loc[[i for i in df_raw.index if x[i].x > 0.5]].copy()
                res['display_name'] = res.apply(lambda r: f"{get_flag(r['nationality'])} {r['player_name']}", axis=1)
                st.session_state.optimized_squad = res
                st.rerun()

with col_pitch:
    st.subheader("Tactical Lineup")
    if 'optimized_squad' in st.session_state:
        st.plotly_chart(create_pitch_figure(st.session_state.optimized_squad), use_container_width=True)
    else:
        st.plotly_chart(create_pitch_figure(), use_container_width=True)

with col_metrics:
    st.subheader("Squad Details")
    if 'optimized_squad' in st.session_state:
        res = st.session_state.optimized_squad

        # Renaming columns for display
        final_table = res[['display_name', 'api_pos', 'team_name', 'market_value_mio']].rename(columns={
            'display_name': 'Player', 'api_pos': 'Position', 'team_name': 'Actual Team',
            'market_value_mio': 'Market Value'
        })

        # Metrics side by side
        m1, m2 = st.columns(2)
        m1.metric("Total Investment", f"€{res['market_value_mio'].sum():.1f}M")
        m2.metric("Balance", f"€{budget - res['market_value_mio'].sum():.1f}M")

        st.dataframe(final_table, hide_index=True, use_container_width=True)