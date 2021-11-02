import pandas as pd
pd.set_option('display.max_columns', None)

import plotly.express as px  # (version 4.7.0 or higher)

import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output  # pip install dash (version 2.0.0 or higher)

from mobiledna.core.appevents import Appevents


app = Dash(__name__)

# -- Import and clean data (importing csv into pandas)
ae = Appevents.load_data('data_qa.csv', sep=';')
df = ae.__data__

ids = df.id.unique()

# ------------------------------------------------------------------------------
# App layout
app.layout = html.Div([

    html.H1("Screen time distribution per category", style={'text-align': 'center'}),

    dcc.Dropdown(id="slct_id",
                 options=[{"label": x, "value": x} for x in ids],
                 multi=False,
                 value=ids[0],
                 style={'width': "40%"}
                 ),
    html.Div(),
    html.Div(id='output_container', children=[]),
    html.Br(),
    dcc.Graph(id='my_mobileDNA_map', figure={}),

    html.H1("", style={'text-align': 'center'}),

])


# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components
@app.callback(
    [Output(component_id='output_container', component_property='children'),
     Output(component_id='my_mobileDNA_map', component_property='figure')],
    [Input(component_id='slct_id', component_property='value')]
)
def update_graph(option_slctd):
    print(option_slctd)
    print(type(option_slctd))

    container = "usage for user with id: {}".format(option_slctd)

    dff = df.copy()
    dff['duration'] = (dff['duration'] / 60)
    dff = dff[dff["id"] == option_slctd]

    dff = dff.groupby(['category'])['duration'].agg(duration='sum')
    dff.reset_index(inplace=True)
    print(dff.head())


    # Plotly Express
    fig = px.pie(
        data_frame=dff,
        values='duration',
        names='category',
        title='screen time per category'
        #template='plotly_dark'
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')

    # Plotly Graph Objects (GO)
    # fig = go.Figure(
    #     data=[go.Choropleth(
    #         locationmode='USA-states',
    #         locations=dff['state_code'],
    #         z=dff["Pct of Colonies Impacted"].astype(float),
    #         colorscale='Reds',
    #     )]
    # )
    #
    # fig.update_layout(
    #     title_text="Bees Affected by Mites in the USA",
    #     title_xanchor="center",
    #     title_font=dict(size=24),
    #     title_x=0.5,
    #     geo=dict(scope='usa'),
    # )

    return container, fig


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)
