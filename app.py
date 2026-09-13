import io
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Pune Helmet-Use Safety Analytics", page_icon="🪖", layout="wide")
REQUIRED=['record_id', 'area_id', 'area_name', 'zone', 'latitude', 'longitude', 'observation_date', 'time_period', 'peak_period', 'vehicle_count', 'motorcycle_count', 'helmet_use_count', 'helmet_nonuse_count', 'helmet_use_rate_pct', 'traffic_volume_index', 'weather_risk_index', 'avg_speed_kmph', 'speed_risk_index', 'road_condition_score', 'road_lighting_score', 'road_width_m', 'rainfall_mm', 'visibility_km', 'intersection_density', 'weather_condition', 'road_condition', 'lighting_condition', 'camera_consent_status', 'observation_confidence']

st.markdown("""
<style>
.stApp{background:#f7f9fc;color:#182230}.block-container{max-width:1500px;padding-top:1.2rem}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid #e5eaf1}
.hero{background:linear-gradient(135deg,#fff,#eef6ff);border:1px solid #dbe7f5;border-radius:20px;padding:25px 30px;margin-bottom:18px}
.hero h1{color:#14213d;font-size:34px;margin:0}.hero p{color:#536174;font-size:15px}
.section{margin:20px 0 10px;color:#14213d;font-size:21px;font-weight:750}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(raw=None):
    if raw is None:
        return pd.read_csv(Path(__file__).parent/"data/sample_pune_helmet_use_safety_records.csv")
    return pd.read_csv(io.BytesIO(raw))

def prepare(d):
    d=d.copy()
    numeric=["latitude","longitude","vehicle_count","motorcycle_count","helmet_use_count","helmet_nonuse_count",
    "helmet_use_rate_pct","traffic_volume_index","weather_risk_index","avg_speed_kmph","speed_risk_index",
    "road_condition_score","road_lighting_score","road_width_m","rainfall_mm","visibility_km",
    "intersection_density","observation_confidence"]
    for c in numeric: d[c]=pd.to_numeric(d[c],errors="coerce")
    d["observation_date"]=pd.to_datetime(d["observation_date"],errors="coerce")
    d=d.dropna(subset=["area_name","latitude","longitude","helmet_use_rate_pct"])
    d["nonuse_gap_pct"]=(100-d["helmet_use_rate_pct"]).clip(0,100)
    d["priority_score"]=(.40*d["nonuse_gap_pct"]+.15*d["traffic_volume_index"]+.12*d["speed_risk_index"]+
    .10*d["weather_risk_index"]+.08*(100-d["road_condition_score"])+.08*(100-d["road_lighting_score"])+
    .07*d["intersection_density"]*100).clip(0,100).round(1)
    d["priority_class"]=pd.cut(d["priority_score"],[-1,25,50,75,101],
    labels=["Low","Moderate","High","Critical"])
    return d

with st.sidebar:
    st.markdown("## 🪖 Pune Safety Control Center")
    upload=st.file_uploader("Upload compatible CSV",type=["csv"])
    raw=load_data(upload.getvalue()) if upload else load_data()
    missing=[c for c in REQUIRED if c not in raw.columns]
    if missing:
        st.error("CSV is missing required columns: "+", ".join(missing))
        st.stop()
    d=prepare(raw)
    zones=sorted(d["zone"].dropna().unique())
    zsel=st.multiselect("Pune zones",zones,zones)
    periods=sorted(d["time_period"].dropna().unique())
    psel=st.multiselect("Time periods",periods,periods)
    rsel=st.slider("Helmet-use rate (%)",0.0,100.0,(0.0,100.0))
    csel=st.slider("Minimum confidence",0.0,1.0,0.60,0.05)

f=d[d["zone"].isin(zsel)&d["time_period"].isin(psel)&
    d["helmet_use_rate_pct"].between(rsel[0],rsel[1])&
    (d["observation_confidence"]>=csel)].copy()

st.markdown("""<div class="hero"><h1>🪖 Pune Helmet-Use Safety Analytics Platform</h1>
<p>Professional local-first screening dashboard for Pune using consented aggregate observations, traffic, weather and road signals.</p></div>""",unsafe_allow_html=True)

m=st.columns(5)
m[0].metric("Records",len(f))
m[1].metric("Motorcycles",f["motorcycle_count"].sum())
m[2].metric("Avg helmet use",f"{f['helmet_use_rate_pct'].mean():.1f}%" if len(f) else "—")
m[3].metric("High + Critical",int(f["priority_class"].isin(["High","Critical"]).sum()))
m[4].metric("Areas",f["area_name"].nunique())

tabs=st.tabs(["Overview","Pune Map","Area Intelligence","Time & Traffic","Scenario Studio","Data Explorer"])

with tabs[0]:
    a,b=st.columns(2)
    q=f["priority_class"].value_counts().reindex(["Low","Moderate","High","Critical"]).fillna(0).reset_index()
    q.columns=["Priority","Records"]
    a.plotly_chart(px.bar(q,x="Priority",y="Records",text_auto=True,title="Priority distribution"),use_container_width=True)
    q=f.groupby("area_name",as_index=False)["priority_score"].mean().sort_values("priority_score",ascending=False).head(12)
    b.plotly_chart(px.bar(q,y="area_name",x="priority_score",orientation="h",text_auto=".1f",title="Highest-priority areas"),use_container_width=True)
    st.info("Screening only: no individual identification, liability determination, causal claims or enforcement prescription.")

with tabs[1]:
    if len(f):
        fig=px.scatter_mapbox(f,lat="latitude",lon="longitude",size="motorcycle_count",color="priority_score",
        hover_name="area_name",hover_data=["zone","time_period","helmet_use_rate_pct","priority_class"],
        zoom=10.5,height=620,color_continuous_scale="Turbo")
        fig.update_layout(mapbox_style="open-street-map",margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig,use_container_width=True)
    else: st.warning("No records match the selected filters.")

with tabs[2]:
    q=f.groupby(["area_id","area_name","zone"],as_index=False).agg(
    observations=("record_id","count"),motorcycles=("motorcycle_count","sum"),
    helmet_use_rate_pct=("helmet_use_rate_pct","mean"),priority_score=("priority_score","mean"),
    traffic_volume_index=("traffic_volume_index","mean")).sort_values("priority_score",ascending=False)
    st.dataframe(q,use_container_width=True,hide_index=True)
    st.download_button("Download area summary",q.to_csv(index=False),"pune_area_summary.csv","text/csv")

with tabs[3]:
    a,b=st.columns(2)
    q=f.groupby("time_period",as_index=False)["helmet_use_rate_pct"].mean()
    a.plotly_chart(px.bar(q,x="time_period",y="helmet_use_rate_pct",text_auto=".1f",title="Helmet-use by time"),use_container_width=True)
    b.plotly_chart(px.scatter(f,x="traffic_volume_index",y="helmet_use_rate_pct",size="motorcycle_count",
    color="priority_score",hover_name="area_name",title="Traffic vs helmet use"),use_container_width=True)
    q=f.groupby("weather_condition",as_index=False).agg(helmet_use_rate_pct=("helmet_use_rate_pct","mean"),
    priority_score=("priority_score","mean"),observations=("record_id","count"))
    st.dataframe(q,use_container_width=True,hide_index=True)

with tabs[4]:
    st.markdown('<div class="section">What-if Safety Planning</div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    improve=a.slider("Helmet-use improvement (pp)",0,30,10)
    traffic=b.slider("Traffic change (%)",-30,30,0)
    visibility=c.slider("Visibility improvement (%)",0,50,10)
    if len(f):
        baseline=float(f["priority_score"].mean())
        s=f.copy()
        s["helmet_use_rate_pct"]=(s["helmet_use_rate_pct"]+improve).clip(0,100)
        s["traffic_volume_index"]=(s["traffic_volume_index"]*(1+traffic/100)).clip(0,100)
        s["visibility_km"]=s["visibility_km"]*(1+visibility/100)
        scenario=(.40*(100-s["helmet_use_rate_pct"])+.15*s["traffic_volume_index"]+.12*s["speed_risk_index"]+
        .10*s["weather_risk_index"]+.08*(100-s["road_condition_score"])+.08*(100-s["road_lighting_score"])+
        .07*s["intersection_density"]*100).clip(0,100)
        new=float(scenario.mean())
        x=st.columns(3)
        x[0].metric("Baseline",f"{baseline:.1f}")
        x[1].metric("Scenario",f"{new:.1f}",delta=f"{new-baseline:+.1f}")
        x[2].metric("Change",f"{new-baseline:+.1f}")

with tabs[5]:
    st.dataframe(f,use_container_width=True,hide_index=True)
    st.download_button("Download filtered CSV",f.to_csv(index=False),"pune_helmet_filtered.csv","text/csv")
    with st.expander("Required CSV schema"):
        st.code("\\n".join(REQUIRED))
