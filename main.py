import streamlit as st
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from google.cloud import bigquery
import os
import base64
import plotly.graph_objects as go

# --- CONFIGURATION & CLIENT ---
PROJECT_ID = 'otimizador-cargas'
JSON_KEY_FILE = "otimizador-cargas-79af1f710cb3.json"


def get_bq_client():
    if os.path.exists(JSON_KEY_FILE):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(JSON_KEY_FILE)
        return bigquery.Client(project=PROJECT_ID)
    elif "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        return bigquery.Client.from_service_account_info(creds_dict, project=PROJECT_ID)
    else:
        st.error("Credentials not found.")
        st.stop()


# --- BACKGROUND & STYLING FUNCTIONS ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()


def set_png_as_page_bg(bin_file):

    try:
        bin_str = get_base64_of_bin_file(bin_file)
        page_bg_img = f'''
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        
        /* FIX: Intelligence Board Header (removes white background) */
        [data-testid="stExpander"] summary {{
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border-radius: 8px;
        }}

        /* Ajuste dos Textos Gerais */
        h1, h2, h3, span, label, p {{
            color: white !important;
        }}

        /* Customização dos Indicadores (Metrics) */
        [data-testid="stMetricValue"] {{
            color: #00D4FF !important; /* Azul neon para destacar os valores */
            font-weight: bold;
        }}
        [data-testid="stMetricLabel"] {{
            color: #CCCCCC !important;
        }}
        
        /* DYNAMIC COLORS FOR THE TABLE NUMBERS */
        .weight-def {{ 
            color: #FFA500 !important; /* Vivid Orange */
            font-weight: bold !important; 
        }}
        .weight-atk {{ 
            color: #00D4FF !important; /* Neon Blue/Cyan */
            font-weight: bold !important; 
        }}

        /* Force table text to be white and background transparent */
        table {{
            background-color: transparent !important;
            color: white !important;
            width: 100%;
        }}

        /* Customização do Botão Optimize Squad */
        div.stButton > button {{
            background-color: #FF4B4B !important;
            color: white !important;
            border-radius: 8px;
            border: 2px solid #FF4B4B;
            width: 100%;
            font-weight: bold;
            transition: 0.3s;
        }}
        div.stButton > button:hover {{
            background-color: white !important;
            color: #FF4B4B !important;
            border: 2px solid white;
        }}

        /* Blur na Sidebar e Cards */
        [data-testid="stSidebar"] {{
            background-color: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
        }}

        .stDataFrame, [data-testid="stExpander"] {{
            background-color: rgba(0, 0, 0, 0.5);
            border-radius: 10px;
        }}
        </style>
        '''
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Arquivo {bin_file} não encontrado.")


def get_flag(country_name):
    """Mapping for nationality flags covering all requested regions"""
    flags = {
        # Original & Major Nations
        "Brazil": "🇧🇷", "Portugal": "🇵🇹", "Argentina": "🇦🇷", "France": "🇫🇷",
        "Germany": "🇩🇪", "Spain": "🇪🇸", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Italy": "🇮🇹",
        "Netherlands": "🇳🇱", "Poland": "🇵🇱", "Belgium": "🇧🇪", "Uruguay": "🇺🇾",
        "Norway": "🇳🇴", "Croatia": "🇭🇷", "Senegal": "🇸🇳", "Morocco": "🇲🇦",

        # New Batch 1
        "Austria": "🇦🇹", "Turkey": "🇹🇷", "Australia": "🇦🇺", "Sweden": "🇸🇪",
        "Denmark": "🇩🇰", "Czech Republic": "🇨🇿", "Syria": "🇸🇾", "Estonia": "🇪🇪",
        "Switzerland": "🇨🇭", "Nigeria": "🇳🇬", "Burkina Faso": "🇧🇫", "Suriname": "🇸🇷",
        "Serbia": "🇷🇸", "Georgia": "🇬🇪", "Slovakia": "🇸🇰", "USA": "🇺🇸", "United States": "🇺🇸",
        "Tunisia": "🇹🇳", "Bosnia-Herzegovina": "🇧🇦",

        # New Batch 2
        "Hungary": "🇭🇺", "Colombia": "🇨🇴", "Canada": "🇨🇦", "Algeria": "🇩🇿",
        "Ivory Coast": "🇨🇮", "Japan": "🇯🇵", "Greece": "🇬🇷", "DR Congo": "🇨🇩",
        "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Luxembourg": "🇱🇺", "Mali": "🇲🇱", "Paraguay": "🇵🇾",
        "Russia": "🇷🇺", "Zimbabwe": "🇿🇼", "Finland": "🇫🇮", "Venezuela": "🇻🇪",
        "Ghana": "🇬🇭", "Ireland": "🇮🇪", "Burundi": "🇧🇮", "Guadeloupe": "🇬🇵",
        "Central African Republic": "🇨🇫",

        # New Batch 3
        "Egypt": "🇪🇬", "French Guiana": "🇬🇫", "Cameroon": "🇨🇲", "Haiti": "🇭🇹",
        "Angola": "🇦🇴", "Northern Ireland": "󠁢󠁥󠁮󠁧󠁿", "Uzbekistan": "🇺🇿", "Slovenia": "🇸🇮",
        "Romania": "🇷🇴", "Jamaica": "🇯🇲", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Ecuador": "🇪🇨",
        "Mexico": "🇲🇽", "New Zealand": "🇳🇿", "Albania": "🇦🇱", "Guinea": "🇬🇳",
        "Cape Verde Islands": "🇨🇻", "Malaysia": "🇲🇾", "Kosovo": "🇽🇰", "Chile": "🇨🇱",
        "Ukraine": "🇺🇦", "North Macedonia": "🇲🇰",

        # New Batch 4
        "Armenia": "🇦🇲", "Lithuania": "🇱🇹", "Indonesia": "🇮🇩", "Guinea-Bissau": "🇬🇼",
        "Equatorial Guinea": "🇬🇶", "Montenegro": "🇲🇪", "Gambia": "🇬🇲", "Zambia": "🇿🇲"
    }
    # .strip() handles any accidental whitespace from the database
    return flags.get(str(country_name).strip(), "🏳️")
@st.cache_data
def load_data():
    client = get_bq_client()
    query = f"SELECT * FROM `{PROJECT_ID}.sports.optimization_final_input`"
    return client.query(query).to_dataframe()


# --- COORDINATES ---
coords_map = {
    'Goalkeeper': [[50, 5]],
    'Right-Back': [[90, 25]], 'Left-Back': [[20, 25]], 'Centre-Back': [[30, 15], [70, 15], [50, 18]],
    'Defensive Midfield': [[40, 40], [60, 40]], 'Central Midfield': [[60, 55], [40, 55], [80, 55]],
    'Attacking Midfield': [[60, 68], [40, 68], [80, 68]],
    'Right Winger': [[85, 80]], 'Left Winger': [[15, 80]], 'Centre-Forward': [[60, 92], [40, 95], [80, 92]]
}


def get_pos_color(pos):
    if pos == 'Goalkeeper': return "GhostWhite"
    if 'Back' in pos or 'Centre-Back' in pos: return "#FF4B4B"
    if 'Midfield' in pos: return "#FFD700"
    return "#00D4FF"


def create_pitch_figure(selected_df=None):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=100,
                  fillcolor="rgba(26, 77, 26, 0.4)", line_color="white", line_width=2, layer='below')
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
                    x=cx, y=cy + 3, text=f"<b>{p['display_name']}</b>", showarrow=False,
                    font=dict(family="Arial Black", size=10, color="white"),
                    bgcolor="rgba(0,0,0,0.8)", borderpad=1, borderwidth=1, bordercolor="white"
                )
                pos_counter[pos] = idx + 1

    fig.update_layout(showlegend=False, height=550, margin=dict(l=5, r=5, b=5, t=5),
                      xaxis=dict(visible=False, range=[0, 100], fixedrange=True),
                      yaxis=dict(visible=False, range=[-10, 100], fixedrange=True),
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    return fig


# --- MAIN APP ---
st.set_page_config(page_title="Elite Scout Optimizer", layout="wide")
set_png_as_page_bg('fundo_app.png')  # Aplica a imagem fundo_app.png

st.title("Elite Squad Optimizer")

df_raw = load_data()

# Sidebar
st.sidebar.header("Strategy Settings")
budget = st.sidebar.slider("Budget (€M)", 50, 600, 300)
formation = st.sidebar.selectbox("Formation", ["4-3-3", "4-4-2", "3-5-2"])

st.sidebar.header("Attribute Multipliers")
m_attack = st.sidebar.slider("Attack Weight", 0.5, 2.0, 1.0)
m_defense = st.sidebar.slider("Defense Weight", 0.5, 2.0, 1.0)

# Multiplier Logic
df_raw['final_score'] = df_raw['performance_score']
df_raw.loc[df_raw['api_pos'].str.contains('Back|Centre-Back|Defensive'), 'final_score'] *= m_defense
df_raw.loc[df_raw['api_pos'].str.contains('Forward|Winger|Attacking'), 'final_score'] *= m_attack

col_pitch, col_metrics = st.columns([0.8, 1])

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
                res['ratio'] = (res['market_value_mio'] / res['final_score']).round(3)
                st.session_state.optimized_squad = res
                st.rerun()

# --- PITCH AND INTELLIGENCE BOARD COLUMN ---
with col_pitch:
    st.subheader("Tactical Lineup")
    # Display the football pitch based on optimized squad state
    if 'optimized_squad' in st.session_state:
        st.plotly_chart(create_pitch_figure(st.session_state.optimized_squad), use_container_width=True)
    else:
        st.plotly_chart(create_pitch_figure(), use_container_width=True)

    # --- PERMANENTLY EXPANDED INTELLIGENCE BOARD ---
    # Setting expanded=True ensures the board is always open
    with st.expander("📖 Detailed Weight Logic", expanded=False):
        st.write(f"Weights applied to base statistics."
                 f"\n Current multipliers: "
                 f"Defense: **{m_defense:.2f}x** | Attack: **{m_attack:.2f}x**")
        # HTML helper functions to inject neon colors into the table
        def fmt_def(val): return f"<span class='weight-def'>{val:.1f}</span>"
        def fmt_atk(val): return f"<span class='weight-atk'>{val:.1f}</span>"
        # Define data directly within the block to avoid NameError
        logic_data = [
            {"Position": "Goalkeeper", "Core Metrics (Base Weight)": f"Saves ({fmt_def(20 * m_defense)})"},
            {"Position": "Full-Backs (R/L)",
             "Core Metrics (Base Weight)": f"Tackles ({fmt_def(8 * m_defense)}), Crosses ({fmt_def(6 * m_defense)}), Prog. Carries ({fmt_def(6 * m_defense)})"},
            {"Position": "Centre-Back",
             "Core Metrics (Base Weight)": f"Tackles ({fmt_def(8 * m_defense)}), Intercept. ({fmt_def(4 * m_defense)}), Blocks ({fmt_def(4 * m_defense)}), Clearances ({fmt_def(4 * m_defense)})"},
            {"Position": "Defensive Midfield",
             "Core Metrics (Base Weight)": f"Tackles ({fmt_def(6 * m_defense)}), Intercept. ({fmt_def(6 * m_defense)}), Prog. Passes ({fmt_def(4 * m_defense)}), Key Passes ({fmt_def(4 * m_defense)})"},
            {"Position": "Central Midfield",
             "Core Metrics (Base Weight)": f"Key Passes ({fmt_atk(4 * m_attack)}), Intercept. ({fmt_def(4 * m_defense)}), Prog. Passes ({fmt_atk(6 * m_attack)}), SCA ({fmt_atk(3 * m_attack)}), Assists ({fmt_atk(3 * m_attack)})"},
            {"Position": "Attacking Midfield",
             "Core Metrics (Base Weight)": f"Key Passes ({fmt_atk(4 * m_attack)}), Assists ({fmt_atk(6 * m_attack)}), Prog. Passes ({fmt_atk(6 * m_attack)}), SCA ({fmt_atk(4 * m_attack)})"},
            {"Position": "Wingers / Offence",
             "Core Metrics (Base Weight)": f"Dribbles ({fmt_atk(4 * m_attack)}), Crosses ({fmt_atk(3 * m_attack)}), xAG ({fmt_atk(3 * m_attack)}), Goals ({fmt_atk(5 * m_attack)}), Assists ({fmt_atk(5 * m_attack)})"},
            {"Position": "Centre-Forward",
             "Core Metrics (Base Weight)": f"Goals ({fmt_atk(8 * m_attack)}), SOT ({fmt_atk(4 * m_attack)}), xG ({fmt_atk(4 * m_attack)}), Assists ({fmt_atk(4 * m_attack)})"}
        ]

        # Create DataFrame and render as HTML to support CSS classes
        df_logic = pd.DataFrame(logic_data)
        st.write(df_logic.to_html(escape=False, index=False), unsafe_allow_html=True)
        st.caption("SCA: Shot Creation Actions | xG: Expected Goals | xAG: Expected Assisted Goals")

with col_metrics:
    st.subheader("Squad Details")
    if 'optimized_squad' in st.session_state:
        res = st.session_state.optimized_squad
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Investment", f"€{res['market_value_mio'].sum():.1f}M")
        m2.metric("Balance", f"€{budget - res['market_value_mio'].sum():.1f}M")
        m3.metric("Avg. Cost Ratio", f"€{(res['market_value_mio'].sum() / res['final_score'].sum()):.4f}")

        final_table = res[['display_name', 'api_pos', 'final_score', 'market_value_mio', 'ratio']].rename(columns={
            'display_name': 'Player', 'api_pos': 'Position', 'final_score': 'Score', 'market_value_mio': 'Value',
            'ratio': 'Ratio'
        })
        st.dataframe(final_table.sort_values(by='Score', ascending=False), hide_index=True, use_container_width=True)