"""
Chart generation using Plotly for SPSS Online
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

PLOTLY_THEME = {
    'template': 'plotly_dark',
    'paper_bgcolor': '#1e2235',
    'plot_bgcolor': '#1e2235',
    'font': {'color': '#c8d0e0', 'family': 'Inter, sans-serif'},
}

COLOR_SEQ = px.colors.qualitative.Set2


def fig_to_json(fig):
    return json.loads(fig.to_json())


class ChartGenerator:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _apply_theme(self, fig, title=''):
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#1e2235',
            plot_bgcolor='#1a1d2e',
            font=dict(color='#c8d0e0', family='Inter, sans-serif'),
            title=dict(text=title, font=dict(size=16, color='#e0e8ff')),
            margin=dict(l=50, r=30, t=60, b=50),
            legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='rgba(255,255,255,0.1)', borderwidth=1),
        )
        fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)', showgrid=True)
        fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)', showgrid=True)
        return fig

    def bar_chart(self, x_var, y_var=None, color_var=None, options=None):
        opts = options or {}
        title = opts.get('title', f'Bar Chart: {x_var}')
        if y_var:
            fig = px.bar(self.df, x=x_var, y=y_var, color=color_var,
                         barmode=opts.get('barmode', 'group'),
                         color_discrete_sequence=COLOR_SEQ)
        else:
            vc = self.df[x_var].value_counts().reset_index()
            vc.columns = [x_var, 'Count']
            fig = px.bar(vc, x=x_var, y='Count', color=x_var,
                         color_discrete_sequence=COLOR_SEQ)
        self._apply_theme(fig, title)
        return fig_to_json(fig)

    def histogram(self, variable, bins=None, color_var=None, options=None):
        opts = options or {}
        title = opts.get('title', f'Histogram: {variable}')
        fig = px.histogram(
            self.df, x=variable, color=color_var,
            nbins=bins or 20,
            marginal=opts.get('marginal', 'box'),
            color_discrete_sequence=COLOR_SEQ,
        )
        self._apply_theme(fig, title)
        return fig_to_json(fig)

    def scatter_plot(self, x_var, y_var, color_var=None, size_var=None, options=None):
        opts = options or {}
        title = opts.get('title', f'Scatter Plot: {x_var} vs {y_var}')
        fig = px.scatter(
            self.df, x=x_var, y=y_var,
            color=color_var, size=size_var,
            trendline=opts.get('trendline', 'ols'),
            color_discrete_sequence=COLOR_SEQ,
        )
        self._apply_theme(fig, title)
        return fig_to_json(fig)

    def box_plot(self, y_var, x_var=None, options=None):
        opts = options or {}
        title = opts.get('title', f'Box Plot: {y_var}')
        fig = px.box(
            self.df, y=y_var, x=x_var,
            points=opts.get('points', 'outliers'),
            color=x_var,
            color_discrete_sequence=COLOR_SEQ,
            notched=opts.get('notched', False),
        )
        self._apply_theme(fig, title)
        return fig_to_json(fig)

    def line_chart(self, x_var, y_vars, options=None):
        opts = options or {}
        title = opts.get('title', f'Line Chart: {y_vars}')
        if isinstance(y_vars, str):
            y_vars = [y_vars]
        fig = go.Figure()
        for i, yv in enumerate(y_vars):
            fig.add_trace(go.Scatter(
                x=self.df[x_var], y=self.df[yv],
                mode='lines+markers', name=yv,
                line=dict(color=COLOR_SEQ[i % len(COLOR_SEQ)], width=2),
                marker=dict(size=6),
            ))
        self._apply_theme(fig, title)
        fig.update_xaxes(title_text=x_var)
        fig.update_yaxes(title_text=', '.join(y_vars))
        return fig_to_json(fig)

    def pie_chart(self, variable, values_var=None, options=None):
        opts = options or {}
        title = opts.get('title', f'Pie Chart: {variable}')
        if values_var:
            agg = self.df.groupby(variable)[values_var].sum().reset_index()
            fig = px.pie(agg, names=variable, values=values_var,
                         color_discrete_sequence=COLOR_SEQ)
        else:
            vc = self.df[variable].value_counts().reset_index()
            vc.columns = [variable, 'Count']
            fig = px.pie(vc, names=variable, values='Count',
                         color_discrete_sequence=COLOR_SEQ,
                         hole=opts.get('hole', 0.3))
        self._apply_theme(fig, title)
        return fig_to_json(fig)
