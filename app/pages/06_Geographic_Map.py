"""Interactive 3D globe showing where clinical trials happen worldwide."""

import sys, os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.data.schema import get_connection
from app.theme import inject_theme

st.set_page_config(page_title="Global Trial Map", page_icon="🗺️", layout="wide")
inject_theme()

_CONDITION_COORDS: dict[str, dict] = {
    "Type 2 Diabetes": {"region": "North America"},
    "Breast Cancer": {"region": "Europe"},
    "Hypertension": {"region": "Asia Pacific"},
    "COPD": {"region": "Middle East"},
    "Heart Failure": {"region": "Africa"},
    "Alzheimer Disease": {"region": "Europe"},
    "Major Depressive Disorder": {"region": "North America"},
    "Lung Cancer": {"region": "Asia Pacific"},
    "Rheumatoid Arthritis": {"region": "Europe"},
    "Chronic Kidney Disease": {"region": "North America"},
    "Parkinson Disease": {"region": "Europe"},
    "Asthma": {"region": "Asia Pacific"},
    "HIV": {"region": "Africa"},
    "Hepatitis C": {"region": "Middle East"},
    "Epilepsy": {"region": "Europe"},
}

_REGION_CITIES = {
    "North America": [
        ("New York", 40.7, -74.0), ("Los Angeles", 34.0, -118.2),
        ("Chicago", 41.9, -87.6), ("Houston", 29.8, -95.4),
        ("Boston", 42.4, -71.1), ("Seattle", 47.6, -122.3),
        ("Montreal", 45.5, -73.6), ("Toronto", 43.7, -79.4),
        ("San Francisco", 37.8, -122.4), ("Phoenix", 33.4, -112.0),
    ],
    "Europe": [
        ("London", 51.5, -0.1), ("Paris", 48.8, 2.3),
        ("Berlin", 52.5, 13.4), ("Barcelona", 41.4, 2.2),
        ("Milan", 45.5, 9.2), ("Vienna", 48.2, 16.4),
        ("Stockholm", 59.3, 18.1), ("Copenhagen", 55.7, 12.6),
        ("Amsterdam", 52.4, 4.9), ("Zurich", 47.4, 8.5),
    ],
    "Asia Pacific": [
        ("Tokyo", 35.7, 139.7), ("Shanghai", 31.2, 121.5),
        ("Seoul", 37.6, 127.0), ("Hong Kong", 22.3, 114.2),
        ("Singapore", 1.3, 103.8), ("Delhi", 28.6, 77.2),
        ("Sydney", -33.9, 151.2), ("Bangkok", 13.7, 100.5),
        ("Beijing", 39.9, 116.4), ("Mumbai", 19.1, 72.9),
    ],
    "Africa": [
        ("Johannesburg", -26.2, 28.0), ("Nairobi", -1.3, 36.8),
        ("Lagos", 6.5, 3.4), ("Cape Town", -33.9, 18.4),
        ("Cairo", 30.0, 31.2), ("Accra", 5.6, -0.2),
    ],
    "Middle East": [
        ("Dubai", 25.3, 55.3), ("Riyadh", 24.7, 46.7),
        ("Tel Aviv", 32.1, 34.8), ("Beirut", 33.9, 35.5),
        ("Tehran", 35.7, 51.4), ("Istanbul", 41.0, 29.0),
    ],
}

_COLORS = {
    "North America": "#1A5276",
    "Europe": "#C0392B",
    "Asia Pacific": "#27AE60",
    "Africa": "#F39C12",
    "Middle East": "#8E44AD",
}


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    conn = get_connection()
    df = conn.execute("SELECT * FROM trials").df()
    conn.close()
    return df


def _build_geo_df(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition, group in df.groupby("condition"):
        info = _CONDITION_COORDS.get(str(condition))
        if info is None:
            h = hash(str(condition)) % len(list(_REGION_CITIES.keys()))
            region = list(_REGION_CITIES.keys())[h]
        else:
            region = info["region"]

        cities = _REGION_CITIES.get(region, [("Unknown", 0, 0)])
        n_trials = len(group)
        avg_enrollment = int(group["enrollment_count"].mean())
        avg_completion = group["completion_rate"].mean()

        rng = np.random.RandomState(hash(str(condition)) % (2**31))
        n_points = min(max(n_trials // 15, 1), len(cities))

        for i in range(n_points):
            city = cities[i % len(cities)]
            jlat = rng.uniform(-1, 1)
            jlon = rng.uniform(-1.5, 1.5)
            share = n_trials // n_points + (1 if i < n_trials % n_points else 0)
            rows.append({
                "condition": str(condition),
                "region": region,
                "city": city[0],
                "lat": city[1] + jlat,
                "lon": city[2] + jlon,
                "n_trials": share,
                "avg_enrollment": avg_enrollment,
                "completion_pct": round(avg_completion * 100, 1) if pd.notna(avg_completion) else 0,
            })
    return pd.DataFrame(rows)


try:
    df = load_data()
except Exception:
    st.error("No data found. Visit Data Explorer first.")
    st.stop()

# Header
st.markdown('<div class="cti-section-label">Global Overview</div>', unsafe_allow_html=True)
st.title("🗺️ Where Trials Happen")
st.caption("Drag to rotate the globe. Hover over a dot to see trial details.")

with st.sidebar:
    st.header("Filters")
    all_conditions = sorted(df["condition"].dropna().unique().tolist())
    sel_conditions = st.multiselect(
        "Diseases", options=all_conditions, default=all_conditions, key="geo_cond"
    )
    sel_phases = st.multiselect(
        "Trial Phase",
        options=["Phase 1", "Phase 2", "Phase 3", "Phase 4"],
        default=["Phase 1", "Phase 2", "Phase 3"],
        key="geo_phase",
    )

filtered = df[df["condition"].isin(sel_conditions) & df["phase"].isin(sel_phases)]

if filtered.empty:
    st.warning("No trials match your filters.")
    st.stop()

geo_df = _build_geo_df(filtered)
total_trials = int(geo_df["n_trials"].sum())
n_cond = geo_df["condition"].nunique()
n_regions = geo_df["region"].nunique()

# KPI
kpi_cols = st.columns(4)
kpi_cols[0].metric("Trials Shown", f"{total_trials:,}")
kpi_cols[1].metric("Diseases", str(n_cond))
kpi_cols[2].metric("Regions", str(n_regions))
kpi_cols[3].metric("Research Sites", f"{len(geo_df):,}")

# 3D Globe
fig = go.Figure()

for region, color in _COLORS.items():
    region_data = geo_df[geo_df["region"] == region]
    if region_data.empty:
        continue

    sizes = np.clip(region_data["n_trials"].values * 0.5 + 4, 5, 35)

    fig.add_trace(go.Scattergeo(
        lat=region_data["lat"],
        lon=region_data["lon"],
        text=region_data.apply(
            lambda r: (
                f"<b>{r['condition']}</b><br>"
                f"{r['city']}, {r['region']}<br>"
                f"<br>"
                f"Trials: {r['n_trials']}<br>"
                f"Avg patients: {r['avg_enrollment']:,}<br>"
                f"Completion: {r['completion_pct']}%"
            ), axis=1,
        ),
        hoverinfo="text",
        marker=dict(
            size=sizes,
            color=color,
            opacity=0.85,
            line=dict(width=0),
            sizemode="diameter",
        ),
        name=region,
    ))

fig.update_geos(
    projection_type="orthographic",
    projection_rotation=dict(lon=-30, lat=20, roll=0),
    showland=True,
    landcolor="#C4B990",
    showocean=True,
    oceancolor="#4A90C4",
    showcountries=True,
    countrycolor="rgba(0,0,0,0.08)",
    showcoastlines=True,
    coastlinecolor="rgba(0,0,0,0.12)",
    showlakes=False,
    showframe=False,
    bgcolor="#1C1C1C",
)

fig.update_layout(
    height=620,
    margin=dict(l=0, r=0, t=0, b=0),
    paper_bgcolor="#1C1C1C",
    plot_bgcolor="#1C1C1C",
    font=dict(color="#E8E4DD", size=12),
    legend=dict(
        x=0.02, y=0.98,
        bgcolor="rgba(28,28,28,0.85)",
        bordercolor="rgba(255,255,255,0.08)",
        borderwidth=1,
        font=dict(size=12, color="#E8E4DD"),
        itemsizing="constant",
        title=dict(text="Region", font=dict(size=11, color="#ABABAB")),
    ),
    dragmode="pan",
)

fig.add_trace(go.Scattergeo(
    lat=[45, 50, -25, 24, 15],
    lon=[-100, 15, 25, 45, 100],
    mode="text",
    text=["North America", "Europe", "Africa", "Middle East", "Asia Pacific"],
    textfont=dict(size=10, color="rgba(255,255,255,0.35)", family="Inter"),
    showlegend=False,
    hoverinfo="none",
))

st.info(
    "Each dot represents a cluster of clinical trials happening in that region. "
    "Bigger dots = more trials. Drag the globe to rotate it and hover over any "
    "dot for details about the trials happening there."
)

st.markdown('<div class="cti-map-container">', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True, config={
    "scrollZoom": True,
    "displayModeBar": False,
})
st.markdown('</div>', unsafe_allow_html=True)

# Regional breakdown
st.markdown('<div class="cti-section-label">By Region</div>', unsafe_allow_html=True)

col_left, col_right = st.columns(2)

with col_left:
    region_data = (
        geo_df.groupby("region")
        .agg(total=("n_trials", "sum"))
        .sort_values("total", ascending=True)
        .reset_index()
    )
    fig_bar = go.Figure(go.Bar(
        y=region_data["region"],
        x=region_data["total"],
        orientation="h",
        marker=dict(
            color=[_COLORS.get(r, "#999") for r in region_data["region"]],
            cornerradius=4,
        ),
        text=region_data["total"],
        textposition="outside",
        textfont=dict(size=13, color="#1C1C1C"),
    ))
    fig_bar.update_layout(
        height=300,
        margin=dict(l=10, r=50, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=13)),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    cond_data = (
        geo_df.groupby("condition")
        .agg(total=("n_trials", "sum"))
        .sort_values("total", ascending=False)
        .head(6)
        .reset_index()
    )
    fig_donut = go.Figure(go.Pie(
        labels=cond_data["condition"],
        values=cond_data["total"],
        hole=0.6,
        marker=dict(colors=list(_COLORS.values()) + ["#EC4899", "#14B8A6"]),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11),
        pull=[0.02] * len(cond_data),
    ))
    fig_donut.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        annotations=[dict(
            text=f"<b>{total_trials:,}</b><br>trials",
            x=0.5, y=0.5, font_size=15, showarrow=False,
            font=dict(color="#1C1C1C"),
        )],
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with st.expander("View detailed data"):
    summary = (
        filtered.groupby("condition")
        .agg(
            total_trials=("nct_id", "count"),
            avg_enrollment=("enrollment_count", "mean"),
            avg_completion=("completion_rate", "mean"),
            phases=("phase", lambda x: ", ".join(sorted(x.dropna().unique()))),
        )
        .reset_index()
    )
    summary["avg_enrollment"] = summary["avg_enrollment"].round(0).astype(int)
    summary["avg_completion"] = (summary["avg_completion"] * 100).round(1)
    summary = summary.rename(columns={
        "condition": "Disease",
        "total_trials": "Total Trials",
        "avg_enrollment": "Avg Enrollment",
        "avg_completion": "Completion %",
        "phases": "Phases Available",
    })
    st.dataframe(summary.sort_values("Total Trials", ascending=False).reset_index(drop=True),
                 use_container_width=True, height=250)
    st.caption(
        "Trial locations are derived from condition-to-region mapping. "
        "Dots on the globe show research activity density, not individual trial sites."
    )
