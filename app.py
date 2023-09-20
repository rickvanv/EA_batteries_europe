import plotly.express as px
from dash.dependencies import Input, Output, State
from dash import dcc, html
import dash_bootstrap_components as dbc
import dash
import pandas as pd
import numpy as np
from entsoe.geo import utils

# Load revenues and spreads data
df_revenues_spreads = pd.read_csv('data/revenues_spreads.csv')


def create_choropleth(year: str, battery_capacity: int, daily_cycle_limit: int):
    '''
    Creates a choropleth graph depicting the revenues per country for a given year.

        Parameters: 
            year: year to depict
            battery_capacity: capacity of battery in [h]
            daily_cycle_limit: limit on number of load cycles the battery can make daily

        Returns:
            fig: plotly express choropleth figure 
    '''
    zones = df_revenues_spreads['zoneName'].unique()
    geo_df = utils.load_zones(zones, pd.Timestamp('20230101'))

    df_revenues_spreads_slice = df_revenues_spreads[
        (df_revenues_spreads['Year'] == year) &
        (df_revenues_spreads['battery_capacity'] == battery_capacity) &
        (df_revenues_spreads['daily_cycle_limit'] == daily_cycle_limit)
    ]
    df_revenues_spreads['Revenue [€/MW/year]'] = df_revenues_spreads['Revenue [€/MW/year]'].round(2)

    geo_df = pd.merge(geo_df, df_revenues_spreads_slice, how="left", on="zoneName")
    geo_df = geo_df.set_index('zoneName')

    fig = px.choropleth(geo_df,
                        geojson=geo_df.geometry,
                        locations=geo_df.index,
                        color=geo_df["Revenue [€/MW/year]"],
                        projection="mercator",
                        range_color=[0, 160*10**3],
                        color_continuous_scale='inferno')
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(height=650,
                      width=750,
                      coloraxis_colorbar_x=0.9
                      )
    return fig


app = dash.Dash(__name__, title="Value of day ahead EA with batteries in Europe",
                external_stylesheets=[dbc.themes.MATERIA])

app.css.config.serve_locally = True
server = app.server

app.layout = dbc.Container(
    fluid=True,
    children=[
        dbc.Row(
            [
                dbc.Col([
                    html.Br(),
                    html.H2(
                        children="Value of performing day ahead EA with batteries in Europe",
                    ),
                    html.Br(),
                    dcc.Interval(id="animate", disabled=True, interval=3500)
                ]),
                dbc.Col([
                        html.Img(
                            src="/assets/vf_logo.png",
                            style={
                                "padding": "10px",
                                "float": "right",
                                "hight": "28%",
                                "width": "28%"
                            },
                            id='vattenfall_img'
                        ),
                        html.P(),
                        ])
            ]
        ),
        dbc.Row([
            dbc.Col([
                html.H3("Select a battery capacity [h]:"),
                dcc.RadioItems(
                    options=[
                        {"label": " 1  ", "value": 1},
                        {"label": " 2  ", "value": 2},
                    ],
                    value=1,
                    id="battery_capacity",
                    className='radio_items',
                    inline=True
                )
            ]),
            dbc.Col([
                html.H3("Select a daily cycle limit:"),
                dcc.RadioItems(
                    options=[
                        {"label": " 1  ", "value": 1},
                        {"label": " 2  ", "value": 2},
                        {"label": " 3  ", "value": 3}
                    ],
                    value=1,
                    id="daily_cycle_limit",
                    className='radio_items',
                    inline=True
                ),
            ],
                class_name='options'
            ),
            html.Br()
        ]),
        dbc.Row([
            html.Br()
        ]),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(html.H1("European map color coded with battery day ahead EA revenues")),
                                dbc.CardBody([
                                    html.H3("Select a year to display:"),
                                    dcc.Slider(2016, 2023, 1,
                                               value=2016,
                                               marks={year: f"{year}" for year in range(2015, 2024)},
                                               id="year_slider"
                                               ),
                                    html.Button("Play/Pause", id="play"),
                                    dcc.Graph(id="choropleth"),
                                    html.P("When a country is not visible on the map, there is no data available for that year."),
                                    html.P("Round-trip efficiency of the battery is taken to be 85%."),
                                    html.P("Revenues of 2023 are linearly scaled to one year.")                        
                                ])
                            ],
                            color="#FCFDFF",
                            outline=False,
                            id="graph_card",
                        )
                    ], width=5
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(html.H1("Bubble chart showing battery day ahead EA revenues per country per year")),
                                dbc.CardBody([
                                    dcc.Graph(id="bubble_chart"),
                                    html.P("Size of the bubbles depict the average daily spread in €/MW.")
                                ])
                            ],
                            color="#FCFDFF",
                            outline=False,
                            id="graph_card2",
                        )
                    ], width=7
                ),
            ]
        ),
    ],
)


@app.callback(
    Output("choropleth", "figure"),
    Output("year_slider", "value"),
    Input("animate", "n_intervals"),
    State("animate", "disabled"),
    Input("year_slider", "value"),
    Input('battery_capacity', "value"),
    Input('daily_cycle_limit', "value"),
)
def update_choropleth_interval(n, interval_disabled: bool, year: str, battery_capacity: int, daily_cycle_limit: int):
    '''
    Updates choropleth graph when the year, battery_capacity or daily cycle limit is changed.
    Year can be changed automatically using the dcc.Interval component.

        Parameters: 
            n: trigger of interval component.
            interval_disabled: True if interval component is incactive. Can be activated by means of play/pause button.
            year: year to depict.
            battery_capacity: capacity of battery in [h].
            daily_cycle_limit: limit on number of load cycles the battery can make daily.

        Returns:
            fig: plotly express choropleth figure.
            year: year to display on dcc.Slider component.
    '''
    if not interval_disabled:
        years = list(range(2016, 2023))  # TODO: change to select years in df_revenues_spreads
        index = years.index(year)
        index = (index + 1) % len(years)
        year = years[index]
    else:
        year = year
    return create_choropleth(year, battery_capacity, daily_cycle_limit), year


@app.callback(
    Output("bubble_chart", "figure"),
    Input('battery_capacity', "value"),
    Input('daily_cycle_limit', "value"))
def bubble_chart(battery_capacity: int, daily_cycle_limit: int):
    '''
    Creates and updates bubble chart showing revenues and spreads for all zones, for the range of years.

        Parameters: 
            battery_capacity: capacity of battery in [h].
            daily_cycle_limit: limit on number of load cycles the battery can make daily.

        Returns:
            fig: plotly express scatterplot figure.
    '''
    df_revenues_spreads_slice = df_revenues_spreads[
        (df_revenues_spreads['battery_capacity'] == battery_capacity) &
        (df_revenues_spreads['daily_cycle_limit'] == daily_cycle_limit)
    ]
    df = df_revenues_spreads_slice.sort_values("zoneName", ascending=False)
    df = df.rename(columns={"zoneName": "Zone", "average_daily_spread": "Average daily spread [€]"})

    fig = px.scatter(
        df, y='Zone', x=df['Year'], color='Revenue [€/MW/year]', size='Average daily spread [€]', 
        range_color=[0, 160*10**3],
        color_continuous_scale='inferno',
    )
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_layout(height=830, width=1060)
    fig.update_coloraxes(colorbar=dict(title='Revenue [€/MW/year]'))
    fig.update_traces(marker=dict(sizeref=0.18))
    fig.update_yaxes(title="Bidding Zone")
    fig.update_xaxes(title='Year', dtick=1)
    fig.update_layout(showlegend=False)
    return fig


@app.callback(
    Output("animate", "disabled"),
    Input("play", "n_clicks"),
    State("animate", "disabled"),
)
def toggle(n, playing):
    '''
    Toggles the interval component on or off based on clicking the play/pause button.

        Parameters: 
            n: button is clicked.
            playing: current state of interval component.

        Returns:
            playing: current state of interval component.
'''
    if n:
        return not playing
    return playing


if __name__ == "__main__":
    app.run_server(debug=True)
