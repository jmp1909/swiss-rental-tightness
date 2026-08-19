"""Plotly figure builders."""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GEOJSON_PATHS = {
    "canton": PROJECT_ROOT / "config" / "cantons.geojson",
    "district": PROJECT_ROOT / "config" / "districts.geojson",
}
FEATURE_ID_KEYS = {
    "canton": "properties.kt_id",
    "district": "properties.bezirk_id",
}

_geojson_cache: dict[str, dict] = {}


def load_geojson(level: str = "canton") -> dict:
    if level not in _geojson_cache:
        _geojson_cache[level] = json.loads(GEOJSON_PATHS[level].read_text(encoding="utf-8"))
    return _geojson_cache[level]


def choropleth(
    df: pd.DataFrame, value_col: str, id_col: str, title: str, color_scale: str, label: str,
    level: str = "canton", hover_name_col: str | None = None,
) -> go.Figure:
    geojson = load_geojson(level)
    fig = px.choropleth(
        df,
        geojson=geojson,
        locations=id_col,
        featureidkey=FEATURE_ID_KEYS[level],
        color=value_col,
        color_continuous_scale=color_scale,
        labels={value_col: label},
        hover_data={id_col: False},
        hover_name=hover_name_col,
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(title=title, margin=dict(l=0, r=0, t=40, b=0))
    return fig


def ranked_bar(df: pd.DataFrame, x: str, y: str, title: str, color: str | None = None) -> go.Figure:
    fig = px.bar(df, x=x, y=y, title=title, color=color, color_continuous_scale="RdYlGn_r" if color else None)
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    return fig


def line_trend(df: pd.DataFrame, x: str, y: str, color: str, title: str, markers: bool = False) -> go.Figure:
    fig = px.line(df, x=x, y=y, color=color, title=title, markers=markers)
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    return fig
