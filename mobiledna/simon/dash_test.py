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
categories = df.category.unique()

# ------------------------------------------------------------------------------
# App layout
app.layout = html.Div(children=[
    html.Div([

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

        dcc.Dropdown(id="slct_id_2",
                     options=[{"label": x, "value": x} for x in ids],
                     multi=False,
                     value=ids[0],
                     style={'width': "40%"}
                     ),
        html.Div(),


        html.Div(id='output_container_3', children=[]),
        dcc.Graph(id='my_mobileDNA_map', figure={}, style={'display': 'inline-block'}),
        dcc.Graph(id='my_mobileDNA_map_3', figure={}, style={'display': 'inline-block'}),
        ]),

    html.Div([

        html.H1("Category usage over time", style={'text-align': 'center'}),

        dcc.Dropdown(id="slct_category",
                     options=[{"label": x, "value": x} for x in categories],
                     multi=False,
                     value=categories[2],
                     style={'width': "40%"}
                     ),
        html.Div(),
        html.Div(id='output_container_2', children=[]),
        html.Br(),
        dcc.Graph(id='my_mobileDNA_map_2', figure={}),

    ]),

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
        title='screen time per category',
        #template='plotly_dark'
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')

    return container, fig

@app.callback(
    [Output(component_id='output_container_3', component_property='children'),
     Output(component_id='my_mobileDNA_map_3', component_property='figure')],
    [Input(component_id='slct_id_2', component_property='value')]
)
def update_graph(option_slctd):

    container = "usage for user with id: {}".format(option_slctd)

    dff = df.copy()
    dff['duration'] = (dff['duration'] / 60)
    dff = dff[dff["id"] == option_slctd]

    dff = dff.groupby(['category'])['duration'].agg(duration='sum')
    dff.reset_index(inplace=True)

    # Plotly Express
    fig = px.pie(
        data_frame=dff,
        values='duration',
        names='category',
        title='screen time per category',
        #template='plotly_dark'
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')

    return container, fig

@app.callback(
    [Output(component_id='output_container_2', component_property='children'),
     Output(component_id='my_mobileDNA_map_2', component_property='figure')],
    [Input(component_id='slct_category', component_property='value')]
)

def update_graph(option_slctd):

    container = "usage in '{}' category for user with id: {}".format(option_slctd, '5e37a125-d7e6-49a1-9f62-b3657f08cdff')

    dff = df.copy()
    dff['duration'] = (dff['duration'] / 60)
    dff = dff[dff["category"] == option_slctd]
    dff = dff[dff["id"] == '5e37a125-d7e6-49a1-9f62-b3657f08cdff']

    dff = dff.groupby(['startDate', 'category'])['duration'].agg(duration='sum')
    dff.reset_index(inplace=True)

    # Plotly Express
    fig = px.bar(
        data_frame=dff,
        x='startDate',
        y='duration',
        color='duration',
        color_continuous_scale='greens',
        # hover_data=['State', 'Pct of Colonies Impacted'],
        labels={'duration': 'duration (min)', 'startDate': 'date'},
        #template='plotly_dark'
    )

    return container, fig


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)
