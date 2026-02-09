import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Unit Economics Autopsy", layout="wide")

# -------------------------
# LOAD DATA
# -------------------------
@st.cache_data
def load_data():
    return pd.read_csv("data/processed/unit_economics.csv")

df = load_data()

# -------------------------
# SIDEBAR FILTERS
# -------------------------
st.sidebar.header("Filters")

# Service type filter
service_types = ["All"] + sorted(df["service_type"].unique().tolist())
selected_service = st.sidebar.selectbox("Service Type", service_types)

# Date range filter (if date column exists)
if "date" in df.columns or "order_date" in df.columns:
    date_col = "date" if "date" in df.columns else "order_date"
    df[date_col] = pd.to_datetime(df[date_col])
    
    min_date = df[date_col].min()
    max_date = df[date_col].max()
    
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        df = df[(df[date_col] >= pd.to_datetime(date_range[0])) & 
                (df[date_col] <= pd.to_datetime(date_range[1]))]

# Apply service type filter
if selected_service != "All":
    df = df[df["service_type"] == selected_service]

# -------------------------
# HEADER
# -------------------------
st.title("📊 Unit Economics Autopsy")
st.markdown(
    """
    **Objective:** Diagnose why revenue growth is not translating into profitability  
    **Audience:** Leadership & Strategy
    """
)

# -------------------------
# KPI METRICS
# -------------------------
total_revenue = df["net_revenue"].sum()
total_cost = df["total_cost"].sum()
total_margin = df["contribution_margin"].sum()
loss_rate = (df["contribution_margin"] < 0).mean()
avg_margin = df["contribution_margin"].mean()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Revenue", f"₹{total_revenue:,.0f}")
col2.metric("Total Cost", f"₹{total_cost:,.0f}")
col3.metric("Total Margin", f"₹{total_margin:,.0f}", 
            delta=f"{(total_margin/total_revenue)*100:.1f}%" if total_revenue > 0 else "0%")
col4.metric("Loss-making Orders", f"{loss_rate:.1%}")
col5.metric("Avg Margin/Order", f"₹{avg_margin:,.2f}")

st.divider()

# -------------------------
# MARGIN DISTRIBUTION
# -------------------------
st.subheader("📈 Margin Distribution")

col_left, col_right = st.columns([2, 1])

with col_left:
    # Interactive histogram with Plotly
    fig_hist = px.histogram(
        df, 
        x="contribution_margin",
        nbins=50,
        title="Distribution of Contribution Margins",
        labels={"contribution_margin": "Contribution Margin (₹)"},
        color_discrete_sequence=["#1f77b4"]
    )
    fig_hist.add_vline(x=0, line_dash="dash", line_color="red", 
                       annotation_text="Break-even", annotation_position="top")
    fig_hist.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_hist, use_container_width=True)

with col_right:
    # Summary stats
    st.markdown("#### Distribution Stats")
    margin_stats = df["contribution_margin"].describe()
    
    stats_df = pd.DataFrame({
        "Metric": ["Min", "25th %ile", "Median", "75th %ile", "Max"],
        "Value": [
            f"₹{margin_stats['min']:,.2f}",
            f"₹{margin_stats['25%']:,.2f}",
            f"₹{margin_stats['50%']:,.2f}",
            f"₹{margin_stats['75%']:,.2f}",
            f"₹{margin_stats['max']:,.2f}"
        ]
    })
    st.dataframe(stats_df, hide_index=True, use_container_width=True)
    
    # Profitable vs unprofitable split
    profitable = (df["contribution_margin"] > 0).sum()
    unprofitable = (df["contribution_margin"] <= 0).sum()
    
    st.markdown(f"""
    **Profitable Orders:** {profitable:,} ({profitable/len(df)*100:.1f}%)  
    **Unprofitable Orders:** {unprofitable:,} ({unprofitable/len(df)*100:.1f}%)
    """)

st.divider()

# -------------------------
# SERVICE TYPE ANALYSIS
# -------------------------
st.subheader("🔍 Profitability by Service Type")

col_chart, col_table = st.columns([2, 1])

with col_chart:
    service_summary = (
        df.groupby("service_type")
        .agg({
            "contribution_margin": "sum",
            "net_revenue": "sum",
            "total_cost": "sum"
        })
        .reset_index()
    )
    service_summary["margin_pct"] = (
        service_summary["contribution_margin"] / service_summary["net_revenue"] * 100
    )
    service_summary = service_summary.sort_values("contribution_margin")
    
    # Interactive bar chart
    fig_service = px.bar(
        service_summary,
        x="contribution_margin",
        y="service_type",
        orientation="h",
        title="Total Contribution Margin by Service Type",
        labels={"contribution_margin": "Total Margin (₹)", "service_type": "Service Type"},
        color="contribution_margin",
        color_continuous_scale=["red", "yellow", "green"],
        text="contribution_margin"
    )
    fig_service.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
    fig_service.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_service, use_container_width=True)

with col_table:
    st.markdown("#### Service Type Metrics")
    summary_display = service_summary.copy()
    summary_display["contribution_margin"] = summary_display["contribution_margin"].apply(lambda x: f"₹{x:,.0f}")
    summary_display["net_revenue"] = summary_display["net_revenue"].apply(lambda x: f"₹{x:,.0f}")
    summary_display["margin_pct"] = summary_display["margin_pct"].apply(lambda x: f"{x:.1f}%")
    
    summary_display = summary_display.rename(columns={
        "service_type": "Service",
        "contribution_margin": "Margin",
        "net_revenue": "Revenue",
        "margin_pct": "Margin %"
    })
    st.dataframe(
        summary_display[["Service", "Revenue", "Margin", "Margin %"]], 
        hide_index=True, 
        use_container_width=True
    )

st.divider()

# -------------------------
# COST BREAKDOWN (if columns exist)
# -------------------------
cost_columns = [col for col in df.columns if 'cost' in col.lower() and col != 'total_cost']
if len(cost_columns) > 1:
    st.subheader("💰 Cost Breakdown Analysis")
    
    cost_breakdown = df[cost_columns].sum().sort_values(ascending=False)
    
    fig_costs = px.pie(
        values=cost_breakdown.values,
        names=cost_breakdown.index,
        title="Cost Distribution",
        hole=0.4
    )
    fig_costs.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_costs, use_container_width=True)

st.divider()

# -------------------------
# SCENARIO SUMMARY
# -------------------------
st.subheader("💡 Key Insights & Recommendations")

insight_col1, insight_col2, insight_col3 = st.columns(3)

with insight_col1:
    st.markdown("""
    #### 🎯 Pricing Opportunity
    Small price increases generate outsized margin impact
    
    **Action:** Review pricing strategy for high-volume, low-margin services
    """)

with insight_col2:
    st.markdown("""
    #### ⚠️ Loss-Making Orders
    Loss-making orders materially drag profitability
    
    **Action:** Identify and address root causes of unprofitable transactions
    """)

with insight_col3:
    st.markdown("""
    #### 🛠️ Cost Optimization
    Support-heavy customers represent a high-leverage intervention point
    
    **Action:** Implement self-service options or tier-based support
    """)

# -------------------------
# DATA EXPLORER (OPTIONAL)
# -------------------------
with st.expander("🔎 Explore Raw Data"):
    st.markdown("Filter and explore the underlying data:")
    
    # Column selector
    display_columns = st.multiselect(
        "Select columns to display",
        options=df.columns.tolist(),
        default=["service_type", "net_revenue", "total_cost", "contribution_margin"][:min(4, len(df.columns))]
    )
    
    if display_columns:
        st.dataframe(df[display_columns].head(100), use_container_width=True)
        
        # Download button
        csv = df[display_columns].to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name="unit_economics_filtered.csv",
            mime="text/csv"
        )

# -------------------------
# FOOTER
# -------------------------
st.markdown("---")
st.markdown(
    f"**Data Summary:** {len(df):,} orders analyzed | "
    f"Total Revenue: ₹{total_revenue:,.0f} | "
    f"Overall Margin: {(total_margin/total_revenue)*100:.1f}%" if total_revenue > 0 else "N/A"
)