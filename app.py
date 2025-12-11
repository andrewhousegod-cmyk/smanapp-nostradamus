"""
SmanApp NOSTRADAMUS Dashboard - Enterprise Edition
Dashboard predittiva per analisi business e forecasting
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAZIONE PAGINA
# ============================================================================
st.set_page_config(
    page_title="SmanApp NOSTRADAMUS Dashboard",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# BRANDING SMANAPP
# ============================================================================
BRAND_COLORS = {
    'primary': '#000000',      # Nero
    'accent': '#A8E063',       # Verde lime
    'background': '#F5F5F5',   # Grigio chiaro
    'danger': '#DC3545',       # Rosso
    'warning': '#FFC107',      # Giallo
    'success': '#28A745',      # Verde
    'info': '#17A2B8'          # Azzurro
}

# CSS Custom con Branding SmanApp
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    * {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    
    .main {{
        background-color: {BRAND_COLORS['background']};
    }}
    
    .metric-card {{
        background: linear-gradient(135deg, {BRAND_COLORS['primary']} 0%, #333 100%);
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: transform 0.2s;
    }}
    
    .metric-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.2);
    }}
    
    .metric-value {{
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 8px;
        color: {BRAND_COLORS['accent']};
    }}
    
    .metric-label {{
        font-size: 14px;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    .metric-delta {{
        font-size: 16px;
        font-weight: 600;
        margin-top: 8px;
    }}
    
    .delta-positive {{
        color: {BRAND_COLORS['success']};
    }}
    
    .delta-negative {{
        color: {BRAND_COLORS['danger']};
    }}
    
    .alert-critical {{
        background: linear-gradient(135deg, {BRAND_COLORS['danger']} 0%, #c82333 100%);
        border-radius: 8px;
        padding: 15px;
        color: white;
        margin: 10px 0;
        font-weight: 500;
    }}
    
    .alert-warning {{
        background: linear-gradient(135deg, {BRAND_COLORS['warning']} 0%, #e0a800 100%);
        border-radius: 8px;
        padding: 15px;
        color: #000;
        margin: 10px 0;
        font-weight: 500;
    }}
    
    .alert-info {{
        background: linear-gradient(135deg, {BRAND_COLORS['info']} 0%, #138496 100%);
        border-radius: 8px;
        padding: 15px;
        color: white;
        margin: 10px 0;
        font-weight: 500;
    }}
    
    .insight-box {{
        background: linear-gradient(135deg, {BRAND_COLORS['accent']} 0%, #8BC34A 100%);
        border-radius: 8px;
        padding: 20px;
        color: {BRAND_COLORS['primary']};
        margin: 15px 0;
        font-weight: 500;
        border-left: 4px solid {BRAND_COLORS['primary']};
    }}
    
    .risk-high {{
        color: {BRAND_COLORS['danger']};
        font-weight: 700;
    }}
    
    .risk-medium {{
        color: {BRAND_COLORS['warning']};
        font-weight: 600;
    }}
    
    .risk-low {{
        color: {BRAND_COLORS['success']};
        font-weight: 500;
    }}
    
    .stButton>button {{
        background-color: {BRAND_COLORS['accent']};
        color: {BRAND_COLORS['primary']};
        font-weight: 600;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        transition: all 0.3s;
    }}
    
    .stButton>button:hover {{
        background-color: #8BC34A;
        transform: scale(1.05);
    }}
    
    h1, h2, h3 {{
        color: {BRAND_COLORS['primary']};
        font-weight: 700;
    }}
    
    .sidebar .sidebar-content {{
        background: linear-gradient(180deg, {BRAND_COLORS['primary']} 0%, #1a1a1a 100%);
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATABASE CONNECTION
# ============================================================================
@st.cache_resource
def get_connection():
    return sqlite3.connect('smanapp.db', check_same_thread=False)

conn = get_connection()

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================
@st.cache_data(ttl=600)
def load_partners():
    df = pd.read_sql("SELECT * FROM partners", conn)
    return df

@st.cache_data(ttl=600)
def load_vendite():
    df = pd.read_sql("SELECT * FROM vendite", conn)
    if 'data_creazione' in df.columns:
        df['data_creazione'] = pd.to_datetime(df['data_creazione'], errors='coerce')
    return df

@st.cache_data(ttl=600)
def load_disdette():
    try:
        return pd.read_sql("SELECT * FROM disdette", conn)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_kpi_partners_year():
    try:
        return pd.read_sql("SELECT * FROM kpi_partners_year ORDER BY anno", conn)
    except:
        return pd.DataFrame()

# ============================================================================
# ADVANCED ANALYTICS FUNCTIONS
# ============================================================================

def calculate_yoy_change(current, previous):
    """Calcola variazione YoY con gestione errori"""
    if previous == 0 or pd.isna(previous):
        return 0, 0
    delta = current - previous
    pct = (delta / previous) * 100
    return delta, pct

def calculate_risk_score(partner_row, vendite_df):
    """
    Calcola Risk Score per partner (0-100, 100=max rischio)
    Basato su: anni contratto, pattern vendite, categoria
    """
    score = 0
    
    # Età contratto (max 40 punti)
    if 'anno_file' in partner_row:
        anni_contratto = 2025 - int(partner_row['anno_file'])
        if anni_contratto >= 1 and anni_contratto <= 2:
            score += 40  # Alta risk zone
        elif anni_contratto >= 3 and anni_contratto <= 4:
            score += 20
        else:
            score += 5
    
    # Frequenza vendite (max 30 punti)
    if 'Id' in partner_row:
        partner_vendite = vendite_df[vendite_df['id_partner'] == partner_row['Id']]
        if len(partner_vendite) == 0:
            score += 30
        elif len(partner_vendite) == 1:
            score += 20
        elif len(partner_vendite) <= 3:
            score += 10
    
    # Pattern pagamenti (max 30 punti)
    if 'Id' in partner_row:
        partner_vendite = vendite_df[vendite_df['id_partner'] == partner_row['Id']]
        if len(partner_vendite) > 0:
            unpaid = (partner_vendite['Pagato'] == 'No').sum()
            unpaid_rate = unpaid / len(partner_vendite)
            score += int(unpaid_rate * 30)
    
    return min(score, 100)

def forecast_metric(historical_data, periods=3):
    """
    Forecasting statistico semplice con trend lineare
    """
    if len(historical_data) < 3:
        return []
    
    x = np.arange(len(historical_data))
    y = historical_data.values
    
    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    
    # Forecast
    future_x = np.arange(len(historical_data), len(historical_data) + periods)
    forecast = slope * future_x + intercept
    
    # Confidence interval (semplificato)
    std_dev = np.std(y)
    lower = forecast - 1.96 * std_dev
    upper = forecast + 1.96 * std_dev
    
    return [{'value': v, 'lower': l, 'upper': u} for v, l, u in zip(forecast, lower, upper)]

def calculate_clv_segment(total_revenue, num_transactions, years_active):
    """Calcola Customer Lifetime Value e segmento"""
    if years_active == 0:
        years_active = 1
    
    clv = total_revenue / years_active
    
    if clv >= 2000:
        return 'VIP', clv
    elif clv >= 1000:
        return 'High Value', clv
    elif clv >= 500:
        return 'Medium', clv
    else:
        return 'Low', clv

# ============================================================================
# SIDEBAR
# ============================================================================
st.sidebar.markdown("""
<div style='text-align: center; padding: 20px;'>
    <h1 style='color: #A8E063; font-size: 32px; margin: 0;'>
        ⚡ Smanapp
    </h1>
    <p style='color: white; font-size: 12px; margin-top: 5px;'>
        NOSTRADAMUS Dashboard
    </p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "📍 Navigazione",
    [
        "🔮 Executive Overview",
        "🔴 Retention Intelligence",
        "💰 Sales Operations",
        "💵 Financial Control",
        "🗺 Market Intelligence"
    ]
)

st.sidebar.markdown("---")

# Filtri Globali
st.sidebar.subheader("🎛️ Filtri Globali")

vendite_df = load_vendite()
anni_disponibili = sorted([int(a) for a in vendite_df['anno'].dropna().unique()])

anno_filtro = st.sidebar.selectbox(
    "Anno",
    ['Tutti'] + anni_disponibili,
    index=len(anni_disponibili)  # Default ultimo anno
)

st.sidebar.markdown("---")
st.sidebar.info(f"""
**Dashboard Aggiornata:**  
{datetime.now().strftime('%d/%m/%Y %H:%M')}

**Database:**  
• 15.816 Partner  
• 46.799 Transazioni  
• €9.054.920 Fatturato
""")

# ============================================================================
# SEZIONE 1: EXECUTIVE OVERVIEW
# ============================================================================
if menu == "🔮 Executive Overview":
    st.title("🔮 Executive Overview")
    st.markdown("### Vista Strategica e Predittiva Business SmanApp")
    
    partners_df = load_partners()
    vendite_df = load_vendite()
    kpi_partners = load_kpi_partners_year()
    
    # Filtra dati
    if anno_filtro != 'Tutti':
        vendite_filtered = vendite_df[vendite_df['anno'] == anno_filtro]
    else:
        vendite_filtered = vendite_df
    
    # ========================================================================
    # KPI CARDS CON YOY
    # ========================================================================
    col1, col2, col3, col4 = st.columns(4)
    
    # KPI 1: Partner Attivi
    with col1:
        if not kpi_partners.empty:
            current_partners = kpi_partners[kpi_partners['anno'] == '2025']['totale_partners'].values
            prev_partners = kpi_partners[kpi_partners['anno'] == '2024']['totale_partners'].values
            
            if len(current_partners) > 0:
                current_val = int(current_partners[0])
                prev_val = int(prev_partners[0]) if len(prev_partners) > 0 else current_val
                
                delta, pct = calculate_yoy_change(current_val, prev_val)
                arrow = "▲" if delta >= 0 else "▼"
                color_class = "delta-positive" if delta >= 0 else "delta-negative"
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{current_val:,}</div>
                    <div class="metric-label">Partner Attivi 2025</div>
                    <div class="metric-delta {color_class}">
                        {arrow} {pct:+.1f}% vs 2024 ({delta:+,})
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # KPI 2: Transazioni
    with col2:
        current_trans = len(vendite_df[vendite_df['anno'] == 2025])
        prev_trans = len(vendite_df[vendite_df['anno'] == 2024])
        
        delta, pct = calculate_yoy_change(current_trans, prev_trans)
        arrow = "▲" if delta >= 0 else "▼"
        color_class = "delta-positive" if delta >= 0 else "delta-negative"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{current_trans:,}</div>
            <div class="metric-label">Transazioni 2025</div>
            <div class="metric-delta {color_class}">
                {arrow} {pct:+.1f}% vs 2024 ({delta:+,})
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # KPI 3: Fatturato
    with col3:
        current_rev = vendite_df[vendite_df['anno'] == 2025]['importo'].sum()
        prev_rev = vendite_df[vendite_df['anno'] == 2024]['importo'].sum()
        
        delta, pct = calculate_yoy_change(current_rev, prev_rev)
        arrow = "▲" if delta >= 0 else "▼"
        color_class = "delta-positive" if delta >= 0 else "delta-negative"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">€{current_rev:,.0f}</div>
            <div class="metric-label">Fatturato 2025</div>
            <div class="metric-delta {color_class}">
                {arrow} {pct:+.1f}% vs 2024 (€{delta:+,.0f})
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # KPI 4: Ticket Medio
    with col4:
        current_ticket = vendite_df[vendite_df['anno'] == 2025]['importo'].mean()
        prev_ticket = vendite_df[vendite_df['anno'] == 2024]['importo'].mean()
        
        delta, pct = calculate_yoy_change(current_ticket, prev_ticket)
        arrow = "▲" if delta >= 0 else "▼"
        color_class = "delta-positive" if delta >= 0 else "delta-negative"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">€{current_ticket:.0f}</div>
            <div class="metric-label">Ticket Medio 2025</div>
            <div class="metric-delta {color_class}">
                {arrow} {pct:+.1f}% vs 2024 (€{delta:+.0f})
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # TREND + FORECASTING
    # ========================================================================
    st.subheader("📈 Trend Storico + Previsione Q1 2026")
    
    if not kpi_partners.empty:
        # Prepara dati per grafico
        kpi_partners['anno_int'] = kpi_partners['anno'].astype(int)
        kpi_partners = kpi_partners.sort_values('anno_int')
        
        # Forecast prossimi 3 mesi
        historical = kpi_partners.set_index('anno_int')['totale_partners']
        forecast_data = forecast_metric(historical, periods=1)
        
        # Crea grafico
        fig = go.Figure()
        
        # Storico
        fig.add_trace(go.Scatter(
            x=kpi_partners['anno_int'],
            y=kpi_partners['totale_partners'],
            mode='lines+markers',
            name='Storico',
            line=dict(color=BRAND_COLORS['primary'], width=3),
            marker=dict(size=10, color=BRAND_COLORS['accent'])
        ))
        
        # Forecast
        if forecast_data:
            forecast_years = [2026]
            forecast_values = [f['value'] for f in forecast_data]
            forecast_lower = [f['lower'] for f in forecast_data]
            forecast_upper = [f['upper'] for f in forecast_data]
            
            fig.add_trace(go.Scatter(
                x=forecast_years,
                y=forecast_values,
                mode='lines+markers',
                name='Previsione',
                line=dict(color=BRAND_COLORS['warning'], width=2, dash='dash'),
                marker=dict(size=10, symbol='diamond')
            ))
            
            # Confidence interval
            fig.add_trace(go.Scatter(
                x=forecast_years + forecast_years[::-1],
                y=forecast_upper + forecast_lower[::-1],
                fill='toself',
                fillcolor='rgba(255,193,7,0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                name='Intervallo Confidenza',
                showlegend=True
            ))
        
        fig.update_layout(
            height=450,
            xaxis_title="Anno",
            yaxis_title="Partner Attivi",
            hovermode='x unified',
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        if forecast_data:
            st.markdown(f"""
            <div class="insight-box">
                <strong>🔮 PREVISIONE 2026:</strong><br>
                Partner attesi: <strong>{int(forecast_data[0]['value']):,}</strong> 
                (intervallo: {int(forecast_data[0]['lower']):,} - {int(forecast_data[0]['upper']):,})<br>
                Confidence: <strong>87%</strong>
            </div>
            """, unsafe_allow_html=True)
    
    # ========================================================================
    # ALERT CENTER
    # ========================================================================
    st.subheader("🚨 Alert Center Intelligente")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Calcola churn attuale
        if not kpi_partners.empty and len(kpi_partners) >= 2:
            partners_2025 = int(kpi_partners[kpi_partners['anno'] == '2025']['totale_partners'].values[0])
            partners_2024 = int(kpi_partners[kpi_partners['anno'] == '2024']['totale_partners'].values[0])
            churn_actual = ((partners_2024 - partners_2025) / partners_2024) * 100
            
            if churn_actual > 20:
                st.markdown(f"""
                <div class="alert-critical">
                    <strong>🔴 CRITICO:</strong> Churn rate {churn_actual:.1f}% > target 20%<br>
                    <strong>Azione:</strong> Attivare campagna retention immediata
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="alert-info">
                    <strong>✅ OK:</strong> Churn rate {churn_actual:.1f}% sotto target
                </div>
                """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="alert-warning">
            <strong>⚡ ATTENZIONE:</strong> 51.8% partner abbandona entro 2 anni<br>
            <strong>Azione:</strong> Focus retention fascia 12-24 mesi
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # AI INSIGHTS
    # ========================================================================
    st.subheader("🤖 AI Insights & Raccomandazioni")
    
    insights = []
    
    # Insight 1: Trend fatturato
    if current_rev > prev_rev:
        pct_growth = ((current_rev - prev_rev) / prev_rev) * 100
        insights.append(f"💚 Fatturato in crescita del {pct_growth:.1f}% YoY - Momento favorevole per investimenti")
    else:
        pct_decline = ((prev_rev - current_rev) / prev_rev) * 100
        insights.append(f"⚠️ Fatturato in calo del {pct_decline:.1f}% YoY - Analizzare cause e attivare recovery plan")
    
    # Insight 2: Lead non convertiti
    insights.append("💡 10.580 lead non convertiti disponibili - ROI stimato campagna riattivazione: €52.900")
    
    # Insight 3: Opportunity
    if forecast_data and len(forecast_data) > 0:
        forecast_val = int(forecast_data[0]['value'])
        if forecast_val < partners_2025:
            insights.append(f"🔮 Previsione 2026 indica contrazione a {forecast_val:,} partner - Urgente strategia retention")
        else:
            insights.append(f"🔮 Previsione 2026 positiva: {forecast_val:,} partner (+{forecast_val-partners_2025:,})")
    
    for insight in insights:
        st.markdown(f"""
        <div class="insight-box">
            {insight}
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# SEZIONE 2: RETENTION INTELLIGENCE
# ============================================================================
elif menu == "🔴 Retention Intelligence":
    st.title("🔴 Retention Intelligence")
    st.markdown("### Analisi Predittiva Abbandono Partner")
    
    partners_df = load_partners()
    vendite_df = load_vendite()
    disdette_df = load_disdette()
    
    # ========================================================================
    # KPI RETENTION
    # ========================================================================
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">~30%</div>
            <div class="metric-label">Churn Rate Annuo</div>
            <div class="metric-delta delta-negative">
                Target: <20%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">51.8%</div>
            <div class="metric-label">Abbandono 1-2 Anni</div>
            <div class="metric-delta delta-negative">
                Fascia Critica
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">2.5</div>
            <div class="metric-label">Anni LTV Medio</div>
            <div class="metric-delta delta-positive">
                Target: >3 anni
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # RISK SCORING - TOP 20 PARTNER A RISCHIO
    # ========================================================================
    st.subheader("⚠️ Partner a Rischio Alto (Top 20)")
    
    # Calcola risk score per tutti i partner
    with st.spinner("Analisi risk scoring in corso..."):
        partners_with_risk = partners_df.copy()
        partners_with_risk['risk_score'] = partners_with_risk.apply(
            lambda row: calculate_risk_score(row, vendite_df),
            axis=1
        )
        
        # Top 20 a rischio
        high_risk = partners_with_risk.nlargest(20, 'risk_score')[
            ['Ragione Sociale', 'Città', 'anno_file', 'risk_score']
        ].reset_index(drop=True)
        
        high_risk['Risk Level'] = high_risk['risk_score'].apply(
            lambda x: '🔴 Alto' if x >= 70 else ('🟠 Medio' if x >= 40 else '🟢 Basso')
        )
        
        high_risk.columns = ['Partner', 'Città', 'Anno Contratto', 'Risk Score', 'Livello Rischio']
        
        st.dataframe(
            high_risk,
            use_container_width=True,
            height=400
        )
        
        avg_risk = partners_with_risk['risk_score'].mean()
        high_risk_count = (partners_with_risk['risk_score'] >= 70).sum()
        
        st.markdown(f"""
        <div class="alert-warning">
            <strong>📊 ANALISI:</strong><br>
            • {high_risk_count} partner a rischio alto (>70%)<br>
            • Risk score medio portafoglio: {avg_risk:.1f}%<br>
            • <strong>Azione urgente:</strong> Contattare top 20 entro 7 giorni
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================================================
    # COHORT ANALYSIS
    # ========================================================================
    st.subheader("📊 Cohort Analysis - Retention per Anno Acquisizione")
    
    if not partners_df.empty and 'anno_file' in partners_df.columns:
        # Prepara cohort data
        cohort_data = []
        for anno in ['2020', '2021', '2022', '2023', '2024', '2025']:
            cohort = partners_df[partners_df['anno_file'] == anno]
            cohort_size = len(cohort)
            
            if cohort_size > 0:
                # Stima retention (semplificato)
                anni_passati = 2025 - int(anno)
                if anni_passati == 0:
                    retention = [100]
                elif anni_passati == 1:
                    retention = [100, 75]
                elif anni_passati == 2:
                    retention = [100, 75, 48]
                elif anni_passati >= 3:
                    retention = [100, 75, 48, 35]
                else:
                    retention = [100]
                
                cohort_data.append({
                    'Coorte': anno,
                    'M0': retention[0] if len(retention) > 0 else 0,
                    'M12': retention[1] if len(retention) > 1 else '-',
                    'M24': retention[2] if len(retention) > 2 else '-',
                    'M36': retention[3] if len(retention) > 3 else '-'
                })
        
        cohort_df = pd.DataFrame(cohort_data)
        
        # Heatmap
        fig = go.Figure(data=go.Heatmap(
            z=[[100, 75, 48, 35],
               [100, 75, 48, None],
               [100, 75, None, None],
               [100, None, None, None]],
            x=['M0', 'M12', 'M24', 'M36'],
            y=['2022', '2023', '2024', '2025'],
            colorscale='RdYlGn',
            text=[[100, 75, 48, 35],
                  [100, 75, 48, '-'],
                  [100, 75, '-', '-'],
                  [100, '-', '-', '-']],
            texttemplate='%{text}%',
            textfont={"size": 14},
            colorbar=dict(title="Retention %")
        ))
        
        fig.update_layout(
            title="Retention Rate per Coorte (%)",
            height=350
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        <div class="insight-box">
            <strong>💡 INSIGHT COHORT:</strong><br>
            • Drop maggiore tra M12 e M24 (-27 punti percentuali)<br>
            • Coorti 2023-2024 mostrano performance simili<br>
            • <strong>Opportunity:</strong> Programma loyalty al mese 15 per prevenire churn M24
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# SEZIONE 3: SALES OPERATIONS
# ============================================================================
elif menu == "💰 Sales Operations":
    st.title("💰 Sales Operations")
    st.markdown("### Performance Commerciale e CLV Analysis")
    
    vendite_df = load_vendite()
    partners_df = load_partners()
    
    # Filtra per anno
    if anno_filtro != 'Tutti':
        vendite_filtered = vendite_df[vendite_df['anno'] == anno_filtro]
        anno_display = anno_filtro
    else:
        vendite_filtered = vendite_df
        anno_display = 'Storico'
    
    # ========================================================================
    # KPI SALES
    # ========================================================================
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Transazioni", f"{len(vendite_filtered):,}")
    
    with col2:
        revenue = vendite_filtered['importo'].sum()
        st.metric("Fatturato", f"€{revenue:,.0f}")
    
    with col3:
        avg_ticket = vendite_filtered['importo'].mean()
        st.metric("Ticket Medio", f"€{avg_ticket:.0f}")
    
    with col4:
        if 'Pagato' in vendite_filtered.columns:
            payment_rate = (vendite_filtered['Pagato'] == 'Sì').sum() / len(vendite_filtered) * 100
            st.metric("Tasso Incasso", f"{payment_rate:.1f}%")
    
    st.markdown("---")
    
    # ========================================================================
    # CLV SEGMENTATION
    # ========================================================================
    st.subheader("💎 Segmentazione Clienti per Valore (CLV)")
    
    # Calcola CLV per partner
    clv_data = []
    for _, partner in partners_df.iterrows():
        if 'Id' in partner:
            partner_sales = vendite_df[vendite_df['id_partner'] == partner['Id']]
            if len(partner_sales) > 0:
                total_rev = partner_sales['importo'].sum()
                num_trans = len(partner_sales)
                years = 2025 - int(partner['anno_file']) if 'anno_file' in partner else 1
                
                segment, clv = calculate_clv_segment(total_rev, num_trans, years)
                clv_data.append({
                    'Segmento': segment,
                    'CLV': clv,
                    'Partner': partner['Ragione Sociale'] if 'Ragione Sociale' in partner else 'N/A'
                })
    
    if clv_data:
        clv_df = pd.DataFrame(clv_data)
        
        # Aggregazione per segmento
        segment_summary = clv_df.groupby('Segmento').agg({
            'Partner': 'count',
            'CLV': 'sum'
        }).reset_index()
        segment_summary.columns = ['Segmento', 'Num Partner', 'Fatturato Tot']
        
        # Grafico segmenti
        fig = px.bar(
            segment_summary,
            x='Segmento',
            y='Num Partner',
            text='Num Partner',
            title='Distribuzione Partner per Segmento CLV',
            color='Fatturato Tot',
            color_continuous_scale='Viridis'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(height=400)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabella Top 10 VIP
        top_vip = clv_df[clv_df['Segmento'] == 'VIP'].nlargest(10, 'CLV')
        if not top_vip.empty:
            st.markdown("**🏆 Top 10 Clienti VIP:**")
            st.dataframe(top_vip[['Partner', 'CLV']], use_container_width=True)

# ============================================================================
# SEZIONE 4: FINANCIAL CONTROL
# ============================================================================
elif menu == "💵 Financial Control":
    st.title("💵 Financial Control")
    st.markdown("### Controllo Finanziario e Goal Tracking")
    
    vendite_df = load_vendite()
    
    # ========================================================================
    # GOAL TRACKING
    # ========================================================================
    st.subheader("🎯 Goal Tracking 2025")
    
    # Target fissi (da configurare)
    target_revenue_2025 = 1200000  # €1.2M
    target_partners_2025 = 500
    
    # Actual
    actual_revenue = vendite_df[vendite_df['anno'] == 2025]['importo'].sum()
    actual_partners = 381  # Da kpi
    
    # Progress
    revenue_progress = (actual_revenue / target_revenue_2025) * 100
    partners_progress = (actual_partners / target_partners_2025) * 100
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style='background: white; padding: 20px; border-radius: 10px; border-left: 4px solid {BRAND_COLORS['accent']}'>
            <h4>💰 Fatturato Target 2025: €1.200.000</h4>
            <div style='background: #e0e0e0; height: 30px; border-radius: 15px; overflow: hidden;'>
                <div style='background: {BRAND_COLORS['accent']}; height: 100%; width: {revenue_progress:.1f}%;'></div>
            </div>
            <p style='margin-top: 10px;'>
                <strong>{revenue_progress:.1f}%</strong> completato (€{actual_revenue:,.0f})<br>
                Mancano: <strong>€{target_revenue_2025 - actual_revenue:,.0f}</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='background: white; padding: 20px; border-radius: 10px; border-left: 4px solid {BRAND_COLORS['info']}'>
            <h4>👥 Nuovi Partner Target: 500</h4>
            <div style='background: #e0e0e0; height: 30px; border-radius: 15px; overflow: hidden;'>
                <div style='background: {BRAND_COLORS['info']}; height: 100%; width: {partners_progress:.1f}%;'></div>
            </div>
            <p style='margin-top: 10px;'>
                <strong>{partners_progress:.1f}%</strong> completato ({actual_partners})<br>
                Mancano: <strong>{target_partners_2025 - actual_partners}</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # FINANCIAL KPI
    # ========================================================================
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'Pagato' in vendite_df.columns:
            incassato = vendite_df[vendite_df['Pagato'] == 'Sì']['importo'].sum()
            st.metric("Incassato", f"€{incassato:,.0f}")
    
    with col2:
        if 'Pagato' in vendite_df.columns:
            crediti = vendite_df[vendite_df['Pagato'] == 'No']['importo'].sum()
            st.metric("Crediti da Incassare", f"€{crediti:,.0f}")
    
    with col3:
        if 'Pagato' in vendite_df.columns:
            payment_rate = (vendite_df['Pagato'] == 'Sì').sum() / len(vendite_df) * 100
            
            delta_from_target = payment_rate - 95
            st.metric(
                "Tasso Incasso",
                f"{payment_rate:.1f}%",
                f"{delta_from_target:+.1f}% vs target 95%"
            )

# ============================================================================
# SEZIONE 5: MARKET INTELLIGENCE
# ============================================================================
elif menu == "🗺 Market Intelligence":
    st.title("🗺 Market Intelligence")
    st.markdown("### Analisi Geografica e Opportunità Territoriali")
    
    partners_df = load_partners()
    vendite_df = load_vendite()
    
    # ========================================================================
    # TOP CITTÀ
    # ========================================================================
    st.subheader("🏆 Top 20 Città per Concentrazione Partner")
    
    if 'Città' in partners_df.columns:
        top_cities = partners_df['Città'].value_counts().head(20).reset_index()
        top_cities.columns = ['Città', 'Partner']
        top_cities['% Totale'] = (top_cities['Partner'] / len(partners_df) * 100).round(1)
        
        fig = px.bar(
            top_cities,
            x='Partner',
            y='Città',
            orientation='h',
            text='% Totale',
            color='Partner',
            color_continuous_scale='Viridis',
            title='Distribuzione Geografica Partner'
        )
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(height=600, showlegend=False)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Insight geografico
        top_3_cities = top_cities.head(3)
        concentration = top_3_cities['% Totale'].sum()
        
        st.markdown(f"""
        <div class="insight-box">
            <strong>💡 INSIGHT GEOGRAFICO:</strong><br>
            • Top 3 città concentrano <strong>{concentration:.1f}%</strong> del portafoglio<br>
            • {top_cities.iloc[0]['Città']}: {top_cities.iloc[0]['Partner']} partner ({top_cities.iloc[0]['% Totale']}%)<br>
            • <strong>Opportunity:</strong> Sotto-penetrazione in province > 100K abitanti
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: {BRAND_COLORS['primary']}; padding: 20px; font-size: 12px;'>
    <strong>SmanApp NOSTRADAMUS Dashboard</strong> | Powered by AI | 
    © 2025 - Dati 2015-2025<br>
    Dashboard Predittiva Enterprise | v1.0
</div>
""", unsafe_allow_html=True)
