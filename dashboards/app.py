# =============================================================================
# app.py — Unit Economics Intelligence Platform
# =============================================================================

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

st.set_page_config(
    page_title="Unit Economics Intelligence",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":      "#0D0F14",
    "surface": "#13161E",
    "border":  "#1E2330",
    "text":    "#E8ECF4",
    "sub":     "#6B758E",
    "accent":  "#4F8EF7",
    "green":   "#2DD4A0",
    "red":     "#F75B5B",
    "orange":  "#F7A24F",
    "purple":  "#A78BFA",
}

CH = {
    "Organic":     C["green"],
    "Referral":    C["purple"],
    "Social":      C["orange"],
    "Paid Search": C["red"],
}

SV = {
    "Express":  C["accent"],
    "Premium":  C["purple"],
    "Standard": C["red"],
}

# ── Base plotly layout ────────────────────────────────────────────────────────
def base_layout(height=360):
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        font=dict(family="monospace", color=C["text"], size=11),
        margin=dict(l=0, r=10, t=36, b=0),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
        xaxis=dict(gridcolor=C["border"], linecolor=C["border"],
                   tickfont=dict(color=C["sub"], size=10)),
        yaxis=dict(gridcolor=C["border"], linecolor=C["border"],
                   tickfont=dict(color=C["sub"], size=10)),
    )

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', sans-serif;
    background: {C["bg"]}; color: {C["text"]};
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 1.2rem 2rem; max-width: 100%; }}

.stTabs [data-baseweb="tab-list"] {{
    background: {C["surface"]}; border: 1px solid {C["border"]};
    border-radius: 8px; padding: 3px; gap: 2px;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent; color: {C["sub"]};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; letter-spacing: 0.06em;
    text-transform: uppercase; border-radius: 5px;
    padding: 7px 16px; border: none;
}}
.stTabs [aria-selected="true"] {{
    background: {C["border"]} !important; color: {C["text"]} !important;
}}

.card {{
    background: {C["surface"]}; border: 1px solid {C["border"]};
    border-radius: 8px; padding: 18px 20px;
    border-top: 2px solid var(--c);
}}
.card-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem; letter-spacing: 0.12em;
    text-transform: uppercase; color: {C["sub"]}; margin-bottom: 6px;
}}
.card-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.6rem; font-weight: 600; line-height: 1;
}}
.card-sub {{
    font-size: 0.72rem; color: {C["sub"]}; margin-top: 4px;
}}

.sec {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem; letter-spacing: 0.14em;
    text-transform: uppercase; color: {C["sub"]};
    border-bottom: 1px solid {C["border"]};
    padding-bottom: 6px; margin: 20px 0 12px 0;
}}

.note {{
    background: {C["surface"]}; border: 1px solid {C["border"]};
    border-left: 2px solid {C["accent"]}; border-radius: 6px;
    padding: 12px 16px; font-size: 0.8rem; color: {C["sub"]};
    line-height: 1.6; margin: 10px 0;
}}
.note strong {{ color: {C["text"]}; }}

.warn {{
    background: rgba(247,91,91,0.04);
    border: 1px solid rgba(247,91,91,0.2);
    border-left: 2px solid {C["red"]}; border-radius: 6px;
    padding: 12px 16px; font-size: 0.8rem; color: {C["sub"]};
    line-height: 1.6; margin: 10px 0;
}}
.warn strong {{ color: {C["red"]}; }}

hr.div {{ border: none; border-top: 1px solid {C["border"]}; margin: 16px 0; }}
</style>
""", unsafe_allow_html=True)


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load():
    p = ROOT_DIR / "data" / "processed"
    o = ROOT_DIR / "data" / "outputs"
    return {
        "ms":   pd.read_csv(p / "monthly_summary.csv"),
        "mc":   pd.read_csv(p / "monthly_costs.csv"),
        "cac":  pd.read_csv(o / "cac_ltv_by_channel.csv"),
        "ct":   pd.read_csv(o / "cac_trend_monthly.csv"),
        "ret":  pd.read_csv(o / "cohort_retention_matrix.csv"),
        "cs":   pd.read_csv(o / "cohort_summary.csv"),
        "ltv":  pd.read_csv(o / "cohort_ltv_curve.csv"),
        "svc":  pd.read_csv(o / "segment_by_service.csv"),
        "reg":  pd.read_csv(o / "segment_by_region.csv"),
        "rh":   pd.read_csv(o / "region_service_heatmap.csv"),
        "scr":  pd.read_csv(o / "segment_cross_tab.csv"),
        "scen": pd.read_csv(o / "scenarios_output.csv"),
        "sens": pd.read_csv(o / "sensitivity_table.csv"),
        "eff":  pd.read_csv(o / "channel_efficiency_score.csv"),
        "cr":   pd.read_csv(o / "channel_reallocation.csv"),
    }

D = load()


# ── Helpers ───────────────────────────────────────────────────────────────────
def inr(v):
    if abs(v) >= 1e7:  return f"₹{v/1e7:.1f}Cr"
    if abs(v) >= 1e5:  return f"₹{v/1e5:.1f}L"
    if abs(v) >= 1e3:  return f"₹{v/1e3:.1f}K"
    return f"₹{v:.0f}"

def card(label, value, sub="", color=None):
    c = color or C["accent"]
    return f"""
    <div class="card" style="--c:{c}">
        <div class="card-label">{label}</div>
        <div class="card-value" style="color:{c}">{value}</div>
        <div class="card-sub">{sub}</div>
    </div>"""

def fig_defaults(fig, height=360, xt="", yt=""):
    fig.update_layout(**base_layout(height))
    if xt: fig.update_xaxes(title_text=xt, title_font=dict(color=C["sub"], size=10))
    if yt: fig.update_yaxes(title_text=yt, title_font=dict(color=C["sub"], size=10))
    return fig


# ── Header ────────────────────────────────────────────────────────────────────
ms = D["ms"]
total_margin = ms["margin"].sum()
status_color = C["red"] if total_margin < 0 else C["green"]
status_text  = "LOSS-MAKING" if total_margin < 0 else "PROFITABLE"

c1, c2 = st.columns([4, 1])
with c1:
    st.markdown(f"""
    <div style="font-family:'IBM Plex Mono',monospace; font-size:1rem; font-weight:600; letter-spacing:0.04em;">
        📉 UNIT ECONOMICS INTELLIGENCE PLATFORM
    </div>
    <div style="font-size:0.78rem; color:{C['sub']}; margin-top:2px;">
        On-demand services diagnostic &nbsp;·&nbsp;
        {ms.iloc[0]['order_month']} → {ms.iloc[-1]['order_month']} &nbsp;·&nbsp;
        20K customers &nbsp;·&nbsp; 200K orders
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div style="text-align:right; padding-top:6px;">
    <span style="background:{status_color}18; color:{status_color};
    border:1px solid {status_color}40; border-radius:5px;
    padding:5px 12px; font-family:'IBM Plex Mono',monospace;
    font-size:0.68rem; font-weight:600; letter-spacing:0.08em;">
    ⚠ {status_text}</span></div>""", unsafe_allow_html=True)

st.markdown("<hr class='div'>", unsafe_allow_html=True)

tabs = st.tabs(["01  OVERVIEW", "02  COHORTS",
                "03  CAC / LTV", "04  SEGMENTS", "05  SCENARIOS"])


# =============================================================================
# TAB 1 — OVERVIEW
# =============================================================================
with tabs[0]:
    total_rev   = ms["revenue"].sum()
    total_ord   = ms["orders"].sum()
    m_first     = ms.iloc[0]["margin_pct"]
    m_last      = ms.iloc[-1]["margin_pct"]
    drift       = m_last - m_first

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.markdown(card("Total Revenue", inr(total_rev), "Jan 2024 – Dec 2025"), unsafe_allow_html=True)
    with k2:
        mc_color = C["red"] if total_margin < 0 else C["green"]
        st.markdown(card("Total Margin", inr(total_margin), "contribution margin", mc_color), unsafe_allow_html=True)
    with k3:
        dc = C["red"] if m_last < 0 else C["green"]
        st.markdown(card("Dec 2025 Margin %", f"{m_last:.1f}%",
                    f"{drift:+.1f}pp vs Jan 2024", dc), unsafe_allow_html=True)
    with k4: st.markdown(card("Total Orders", f"{int(total_ord):,}", "across 24 months", C["purple"]), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    cl, cr = st.columns([3, 2])

    with cl:
        st.markdown("<div class='sec'>Monthly margin % — Jan 2024 → Dec 2025</div>", unsafe_allow_html=True)
        months = ms["order_month"].tolist()
        mvals  = ms["margin_pct"].tolist()
        fig = go.Figure()
        fig.add_hline(y=0, line_dash="dot", line_color=C["border"], line_width=1)
        fig.add_trace(go.Scatter(
            x=months, y=[v if v>=0 else 0 for v in mvals],
            fill="tozeroy", fillcolor="rgba(45,212,160,0.07)",
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=months, y=[v if v<=0 else 0 for v in mvals],
            fill="tozeroy", fillcolor="rgba(247,91,91,0.07)",
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=months, y=mvals, mode="lines+markers",
            line=dict(color=C["accent"], width=2),
            marker=dict(color=[C["green"] if v>=0 else C["red"] for v in mvals],
                        size=5, line=dict(color=C["bg"], width=1)),
            hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>"))
        fig = fig_defaults(fig, 320, yt="Margin %")
        fig.update_xaxes(tickangle=-45, tickfont=dict(size=9))
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        st.markdown("<div class='sec'>Avg cost per order — by type</div>", unsafe_allow_html=True)
        mc = D["mc"].copy()
        mc["var"] = mc["variable_cost"] / ms["orders"]
        mc["del"] = mc["delivery_cost"] / ms["orders"]
        mc["sup"] = mc["support_cost"]  / ms["orders"]
        fig2 = go.Figure()
        for col, label, color in [("var","Variable",C["accent"]),
                                   ("del","Delivery",C["orange"]),
                                   ("sup","Support",C["red"])]:
            fig2.add_trace(go.Scatter(
                x=mc["order_month"], y=mc[col],
                name=label, mode="lines",
                line=dict(color=color, width=2),
                stackgroup="one",
                hovertemplate=f"{label}: ₹%{{y:.1f}}<extra></extra>"))
        fig2 = fig_defaults(fig2, 320, yt="₹ / order")
        fig2.update_xaxes(tickangle=-45, tickfont=dict(size=9))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"""<div class="warn">
        <strong>Core finding:</strong> Margin collapsed from <strong>+13.7%</strong> (Jan 2024)
        to <strong>-7.5%</strong> (Dec 2025) — a 21pp decline. Revenue grew but delivery cost
        inflation (+30% over 2 years) and recurring support cost spikes erased all gains.
        The business is structurally loss-making at the unit level.
    </div>""", unsafe_allow_html=True)


# =============================================================================
# TAB 2 — COHORTS
# =============================================================================
with tabs[1]:
    cs = D["cs"]
    avg_m1  = cs["m1_retention"].mean() * 100
    avg_ltv = cs["avg_ltv"].mean()

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.markdown(card("Avg M1 Retention", f"{avg_m1:.1f}%", "month 1 re-order rate"), unsafe_allow_html=True)
    with k2:
        ltv_c = C["red"] if avg_ltv < 0 else C["green"]
        st.markdown(card("Avg LTV / Customer", inr(avg_ltv), "lifetime contribution margin", ltv_c), unsafe_allow_html=True)
    with k3: st.markdown(card("Best Cohort", cs.loc[cs["avg_ltv"].idxmax(),"cohort"], "highest LTV", C["green"]), unsafe_allow_html=True)
    with k4: st.markdown(card("Worst Cohort", cs.loc[cs["avg_ltv"].idxmin(),"cohort"], "lowest LTV", C["red"]), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='sec'>Retention matrix — % of cohort still active at month N</div>", unsafe_allow_html=True)

    ret = D["ret"]
    mcols = [c for c in ret.columns if c.startswith("M")]
    z = [[None if (isinstance(v,float) and np.isnan(v)) else round(v*100,1)
          for v in row] for row in ret[mcols].values]

    fig = go.Figure(go.Heatmap(
        z=z, x=mcols, y=ret["cohort"].tolist(),
        colorscale=[[0,"rgba(247,91,91,0.85)"],[0.2,"rgba(247,162,79,0.7)"],
                    [0.4,"rgba(247,226,79,0.6)"],[0.7,"rgba(45,212,160,0.8)"],
                    [1,"rgba(79,142,247,0.9)"]],
        zmin=0, zmax=100,
        text=[[f"{v}%" if v is not None else "" for v in row] for row in z],
        texttemplate="%{text}",
        textfont=dict(size=8, family="monospace"),
        hovertemplate="Cohort <b>%{y}</b> · Month <b>%{x}</b> · <b>%{z}%</b><extra></extra>",
        colorbar=dict(tickfont=dict(color=C["sub"]),
                      outlinecolor=C["border"], outlinewidth=1,
                      title=dict(text="%", font=dict(color=C["sub"]))),
    ))
    fig = fig_defaults(fig, 480)
    fig.update_xaxes(side="top", tickfont=dict(size=9))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=9))
    st.plotly_chart(fig, use_container_width=True)

    cl, cr = st.columns(2)
    with cl:
        st.markdown("<div class='sec'>Average cumulative LTV curve</div>", unsafe_allow_html=True)
        ltv = D["ltv"]
        fig2 = go.Figure()
        fig2.add_hline(y=0, line_dash="dot", line_color=C["border"], line_width=1)
        fig2.add_trace(go.Scatter(
            x=ltv["month_number"], y=ltv["avg_cum_margin"],
            mode="lines+markers", line=dict(color=C["accent"], width=2),
            marker=dict(size=4, color=C["accent"]),
            fill="tozeroy", fillcolor="rgba(79,142,247,0.06)",
            hovertemplate="Month %{x} · ₹%{y:.2f}<extra></extra>"))
        fig2 = fig_defaults(fig2, 280, xt="Months since signup", yt="Avg cumulative margin ₹")
        st.plotly_chart(fig2, use_container_width=True)

    with cr:
        st.markdown("<div class='sec'>LTV per customer by cohort</div>", unsafe_allow_html=True)
        cs2 = cs.sort_values("cohort")
        fig3 = go.Figure(go.Bar(
            x=cs2["cohort"], y=cs2["avg_ltv"],
            marker_color=[C["green"] if v>=0 else C["red"] for v in cs2["avg_ltv"]],
            marker_line_width=0,
            hovertemplate="<b>%{x}</b> · ₹%{y:.2f}<extra></extra>"))
        fig3.add_hline(y=0, line_dash="dot", line_color=C["sub"], line_width=1)
        fig3 = fig_defaults(fig3, 280, yt="Avg LTV ₹")
        fig3.update_xaxes(tickangle=-45, tickfont=dict(size=8))
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown(f"""<div class="note">
        <strong>Key insight:</strong> Newer cohorts (2025) have <strong>higher M1 retention</strong>
        but <strong>worse LTV</strong> than older cohorts. The 2024-01 cohort retains at just 68.9%
        but generates positive LTV. This is an <strong>acquisition quality problem</strong> —
        recent customers come from channels with worse economics and generate more support cost per order.
    </div>""", unsafe_allow_html=True)


# =============================================================================
# TAB 3 — CAC / LTV
# =============================================================================
with tabs[2]:
    cac = D["cac"]
    organic = cac[cac["acquisition_channel"]=="Organic"].iloc[0]
    paid    = cac[cac["acquisition_channel"]=="Paid Search"].iloc[0]

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.markdown(card("Organic CAC", inr(organic["cac"]), "lowest cost channel", C["green"]), unsafe_allow_html=True)
    with k2: st.markdown(card("Paid Search CAC", inr(paid["cac"]), "4.3× more expensive than Organic", C["red"]), unsafe_allow_html=True)
    with k3: st.markdown(card("Only Positive LTV", "Organic", f"₹{organic['avg_ltv']:.2f} / customer", C["green"]), unsafe_allow_html=True)
    with k4: st.markdown(card("Channels Recovered CAC", "0 / 4", "none reach payback", C["red"]), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    cl, cr = st.columns([3, 2])

    with cl:
        st.markdown("<div class='sec'>CAC vs average LTV by channel</div>", unsafe_allow_html=True)
        channels = cac["acquisition_channel"].tolist()
        ch_cols  = [CH.get(c, C["accent"]) for c in channels]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="CAC", x=channels, y=cac["cac"],
            marker_color=ch_cols, marker_opacity=0.45, marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>CAC: ₹%{y:.2f}<extra></extra>"))
        fig.add_trace(go.Bar(
            name="Avg LTV", x=channels, y=cac["avg_ltv"],
            marker_color=ch_cols, marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>LTV: ₹%{y:.2f}<extra></extra>"))
        fig.add_hline(y=0, line_color=C["sub"], line_width=1, line_dash="dot")
        fig.update_layout(barmode="group")
        fig = fig_defaults(fig, 320, yt="₹")
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        st.markdown("<div class='sec'>Channel efficiency rank</div>", unsafe_allow_html=True)
        eff = D["eff"].sort_values("efficiency_score", ascending=True)
        fig2 = go.Figure(go.Bar(
            x=eff["efficiency_score"], y=eff["acquisition_channel"],
            orientation="h",
            marker_color=[CH.get(c, C["accent"]) for c in eff["acquisition_channel"]],
            marker_line_width=0,
            text=[f"{v:.3f}" for v in eff["efficiency_score"]],
            textposition="outside",
            textfont=dict(size=11, color=C["text"]),
            hovertemplate="<b>%{y}</b> · %{x:.3f}<extra></extra>"))
        fig2 = fig_defaults(fig2, 320, xt="Composite score (0–1)")
        fig2.update_xaxes(range=[0, 1.15])
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<div class='sec'>Monthly CAC trend by channel</div>", unsafe_allow_html=True)
    ct = D["ct"]
    ct = ct[ct["monthly_cac"].notna() & (ct["monthly_cac"] > 0)]
    fig3 = go.Figure()
    for ch in ct["acquisition_channel"].unique():
        sub = ct[ct["acquisition_channel"]==ch].sort_values("month")
        fig3.add_trace(go.Scatter(
            x=sub["month"], y=sub["monthly_cac"],
            name=ch, mode="lines",
            line=dict(color=CH.get(ch, C["accent"]), width=2),
            hovertemplate=f"<b>{ch}</b> · %{{x}}<br>CAC: ₹%{{y:.2f}}<extra></extra>"))
    fig3 = fig_defaults(fig3, 280, yt="CAC ₹")
    fig3.update_xaxes(tickangle=-45, tickfont=dict(size=9))
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown(f"""<div class="warn">
        <strong>Critical finding:</strong> Every channel has LTV:CAC below 1.0x — benchmark is 3.0x.
        <strong>Paid Search</strong> costs ₹{paid['cac']:.0f} to acquire a customer who generates
        <strong>-₹{abs(paid['avg_ltv']):.2f}</strong> lifetime margin.
        Net loss of ₹{abs(paid['net_value_after_cac']):.0f} per customer. Paid Search drives 45% of acquisition.
    </div>""", unsafe_allow_html=True)


# =============================================================================
# TAB 4 — SEGMENTS
# =============================================================================
with tabs[3]:
    svc = D["svc"]
    reg = D["reg"]

    std = svc[svc["service_type"]=="Standard"].iloc[0]
    worst_reg = reg.loc[reg["margin_pct"].idxmin()]

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.markdown(card("Standard Margin %", f"{std['margin_pct']:.1f}%", "biggest margin destroyer", C["red"]), unsafe_allow_html=True)
    with k2: st.markdown(card("Express Margin %", f"{svc[svc['service_type']=='Express'].iloc[0]['margin_pct']:.1f}%", "best performing service", C["green"]), unsafe_allow_html=True)
    with k3: st.markdown(card("Worst Region", worst_reg["region"], f"{worst_reg['margin_pct']:.1f}% margin", C["red"]), unsafe_allow_html=True)
    with k4: st.markdown(card("All Regions", "Loss-making", "no region is profitable", C["red"]), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    cl, cr = st.columns(2)

    with cl:
        st.markdown("<div class='sec'>Margin % by service type</div>", unsafe_allow_html=True)
        svc2 = svc.sort_values("margin_pct")
        fig = go.Figure(go.Bar(
            x=svc2["service_type"], y=svc2["margin_pct"],
            marker_color=[SV.get(s, C["accent"]) for s in svc2["service_type"]],
            marker_line_width=0,
            text=[f"{v:.1f}%" for v in svc2["margin_pct"]],
            textposition="outside",
            textfont=dict(size=13, color=C["text"]),
            hovertemplate="<b>%{x}</b> · %{y:.1f}%<extra></extra>"))
        fig.add_hline(y=0, line_dash="dot", line_color=C["sub"], line_width=1)
        fig = fig_defaults(fig, 300, yt="Margin %")
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        st.markdown("<div class='sec'>Margin % by region</div>", unsafe_allow_html=True)
        reg2 = reg.sort_values("margin_pct")
        fig2 = go.Figure(go.Bar(
            x=reg2["region"], y=reg2["margin_pct"],
            marker_color=[C["red"] if v<0 else C["green"] for v in reg2["margin_pct"]],
            marker_line_width=0,
            text=[f"{v:.1f}%" for v in reg2["margin_pct"]],
            textposition="outside",
            textfont=dict(size=13, color=C["text"]),
            hovertemplate="<b>%{x}</b> · %{y:.1f}%<extra></extra>"))
        fig2.add_hline(y=0, line_dash="dot", line_color=C["sub"], line_width=1)
        fig2 = fig_defaults(fig2, 300, yt="Margin %")
        st.plotly_chart(fig2, use_container_width=True)

    cl2, cr2 = st.columns(2)

    with cl2:
        st.markdown("<div class='sec'>Region × Service — margin % heatmap</div>", unsafe_allow_html=True)
        rh = D["rh"].set_index("region")
        services = ["Express", "Premium", "Standard"]
        services = [s for s in services if s in rh.columns]
        z_rh = rh[services].values.tolist()
        fig3 = go.Figure(go.Heatmap(
            z=z_rh, x=services, y=rh.index.tolist(),
            colorscale=[[0,"rgba(247,91,91,0.85)"],[0.5,"rgba(247,226,79,0.5)"],
                        [1,"rgba(45,212,160,0.85)"]],
            text=[[f"{v:.1f}%" for v in row] for row in z_rh],
            texttemplate="%{text}",
            textfont=dict(size=13, family="monospace"),
            hovertemplate="<b>%{y}</b> × <b>%{x}</b> · %{z:.1f}%<extra></extra>",
            colorbar=dict(tickfont=dict(color=C["sub"]),
                          outlinecolor=C["border"], outlinewidth=1,
                          title=dict(text="%", font=dict(color=C["sub"]))),
        ))
        fig3 = fig_defaults(fig3, 300)
        st.plotly_chart(fig3, use_container_width=True)

    with cr2:
        st.markdown("<div class='sec'>Service × Channel — margin % cross-tab</div>", unsafe_allow_html=True)
        scr = D["scr"].set_index("service_type")
        channels_scr = [c for c in ["Organic","Paid Search","Referral","Social"] if c in scr.columns]
        z_scr = scr[channels_scr].values.tolist()
        fig4 = go.Figure(go.Heatmap(
            z=z_scr, x=channels_scr, y=scr.index.tolist(),
            colorscale=[[0,"rgba(247,91,91,0.85)"],[0.5,"rgba(247,226,79,0.5)"],
                        [1,"rgba(45,212,160,0.85)"]],
            text=[[f"{v:.1f}%" for v in row] for row in z_scr],
            texttemplate="%{text}",
            textfont=dict(size=13, family="monospace"),
            hovertemplate="<b>%{y}</b> × <b>%{x}</b> · %{z:.1f}%<extra></extra>",
            colorbar=dict(tickfont=dict(color=C["sub"]),
                          outlinecolor=C["border"], outlinewidth=1,
                          title=dict(text="%", font=dict(color=C["sub"]))),
        ))
        fig4 = fig_defaults(fig4, 300)
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown(f"""<div class="note">
        <strong>Key finding:</strong> <strong>Standard service destroys ₹8.7L in margin</strong> (-17.7%).
        Its support cost is 27.8% of revenue vs 10.6% for Express. All regions are loss-making.
        The fix is either repricing Standard, reducing its support cost, or shifting
        volume toward Express and Premium which remain margin-positive.
    </div>""", unsafe_allow_html=True)


# =============================================================================
# TAB 5 — SCENARIOS
# =============================================================================
with tabs[4]:
    scen     = D["scen"]
    sens     = D["sens"]
    baseline = scen["baseline_margin"].iloc[0]

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.markdown(card("Baseline Margin", inr(baseline), "current state", C["red"]), unsafe_allow_html=True)
    with k2: st.markdown(card("Best Single Lever", inr(scen.iloc[0]["margin_delta"]), scen.iloc[0]["scenario"][:30]+"…", C["green"]), unsafe_allow_html=True)
    with k3: st.markdown(card("Best Combined", inr(scen[scen["category"]=="Combined"].iloc[0]["new_margin"]), "+price +support cut +remove losses", C["green"]), unsafe_allow_html=True)
    with k4: st.markdown(card("Scenarios Modelled", str(len(scen)), "across 5 lever categories", C["accent"]), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='sec'>All scenarios — ranked by margin impact</div>", unsafe_allow_html=True)

    scen_s = scen.sort_values("margin_delta", ascending=True)
    fig = go.Figure(go.Bar(
        x=scen_s["margin_delta"], y=scen_s["scenario"],
        orientation="h",
        marker_color=[C["green"] if v>=0 else C["red"] for v in scen_s["margin_delta"]],
        marker_line_width=0,
        text=[inr(v) for v in scen_s["margin_delta"]],
        textposition="outside",
        textfont=dict(size=10, color=C["text"]),
        hovertemplate="<b>%{y}</b><br>Impact: ₹%{x:,.0f}<extra></extra>"))
    fig.add_vline(x=0, line_color=C["sub"], line_width=1, line_dash="dot")
    fig = fig_defaults(fig, 480, xt="Margin delta (₹)")
    fig.update_yaxes(tickfont=dict(size=9))
    st.plotly_chart(fig, use_container_width=True)

    cl, cr = st.columns([3, 2])

    with cl:
        st.markdown("<div class='sec'>Sensitivity — price increase × support cost reduction</div>", unsafe_allow_html=True)
        s2 = sens.rename(columns={
            "price_increase_pct": "Price ↑",
            "support_cut_0pct":   "-0%",
            "support_cut_10pct":  "-10%",
            "support_cut_15pct":  "-15%",
            "support_cut_20pct":  "-20%",
            "support_cut_25pct":  "-25%",
        })
        num_cols = [c for c in s2.columns if c != "Price ↑"]
        styled = s2.style\
            .applymap(lambda v: f"color:{C['green']}" if isinstance(v,(int,float)) and v>0
                      else f"color:{C['red']}" if isinstance(v,(int,float)) and v<0 else "",
                      subset=num_cols)\
            .format({c: "₹{:,.0f}" for c in num_cols})\
            .set_properties(**{
                "background-color": C["surface"],
                "color": C["text"],
                "font-family": "monospace",
                "font-size": "12px",
            })
        st.dataframe(styled, use_container_width=True, height=220)

    with cr:
        st.markdown(f"""<div class="note" style="margin-top:28px">
            <strong>How to read:</strong><br><br>
            Each cell = total margin if both levers are applied together.
            Rows = price increase. Columns = support cost reduction.<br><br>
            <span style="color:{C['red']}">Red = still loss-making</span><br>
            <span style="color:{C['green']}">Green = profitable</span><br><br>
            A 5% price rise alone is insufficient.
            Combined with 15% support reduction, the business turns profitable.
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="note">
        <strong>Recommendation:</strong> The highest-impact single action is
        <strong>removing deep loss orders</strong> (margin &lt; -₹50) — 14,732 orders (7.4% of volume)
        causing disproportionate losses. Combined with a 5% price increase and 15% support cost
        reduction, the model projects a <strong>+₹23L margin improvement</strong>,
        turning the business from {inr(baseline)} to strongly positive.
    </div>""", unsafe_allow_html=True)

    st.markdown("<hr class='div'>", unsafe_allow_html=True)
    st.markdown(f"""<div style="text-align:center; color:{C['sub']};
    font-family:monospace; font-size:0.6rem; letter-spacing:0.1em; padding:4px 0;">
    UNIT ECONOMICS INTELLIGENCE PLATFORM · SYNTHETIC DATA · 20K CUSTOMERS · 200K ORDERS · 2024–2025
    </div>""", unsafe_allow_html=True)