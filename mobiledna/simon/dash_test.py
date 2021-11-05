import pandas as pd

import plotly.express as px  # (version 4.7.0 or higher)
import plotly.graph_objects as go

from dash import Dash, dcc, html, Input, Output  # pip install dash (version 2.0.0 or higher)

from mobiledna.core.appevents import Appevents


app = Dash(__name__)

# -- Import and clean data (importing csv into pandas)
ae = Appevents.load_data('data_qa.csv', sep=';')
df = ae.__data__

# -- Options for dropdown list
ids = df.id.unique()
categories = df.category.unique()
tods = df.startTOD.unique()

# ------------------------------------------------------------------------------
# App layout
app.layout = html.Div(children=[
    html.Div([

        html.H1("Screen time distribution per category", style={'text-align': 'center'}),

        html.Div([
        dcc.Dropdown(id="slct_id",
                     options=[{"label": x, "value": x} for x in ids],
                     placeholder="Select an id",
                     multi=False,
                     value=ids[0],
                     style={'width': "49%", 'display':'inline-block'},
                     ),

        dcc.Dropdown(id="slct_id_2",
                     options=[{"label": x, "value": x} for x in ids],
                     placeholder="Select an id",
                     multi=False,
                     value=ids[0],
                     style={'width': "49%", 'display':'inline-block'},
                     ),
        ]),

        html.Div(id='output_container', children=[], style={'text-align': 'left', 'width': "49%", 'display': 'inline-block'}),
        html.Div(id='output_container_2', children=[], style={'text-align': 'left', 'width': "49%", 'display': 'inline-block'}),

        html.Div(),
        dcc.Graph(id='my_mobileDNA_map', figure={}, style={'width': "49%", 'display': 'inline-block'}),
        dcc.Graph(id='my_mobileDNA_map_2', figure={}, style={'width': "49%", 'display': 'inline-block'}),
        ]),

    html.Div([

        html.H1("Category usage over time", style={'text-align': 'center'}),
        dcc.Dropdown(id="slct_id_3",
                     options=[{"label": x, "value": x} for x in ids],
                     multi=False,
                     placeholder="Select an id",
                     value=ids[1],
                     style={'width': "40%"}
                     ),

        dcc.Dropdown(id="slct_category",
                     options=[{"label": x, "value": x} for x in categories],
                     multi=False,
                     placeholder="Select a category",
                     value=categories[1],
                     style={'width': "40%"}
                     ),
        html.Div(),
        html.Div(id='output_container_3', children=[]),
        html.Br(),
        dcc.Graph(id='my_mobileDNA_map_3', figure={}),

    ]),

    html.Div([

        html.H1("Location of app use", style={'text-align': 'center'}),

        dcc.RadioItems(id="slct_tod",
                     options=[{"label": x, "value": x} for x in tods],
                     value=tods[0],
                     style={'width': "100%", 'text-align':'center'}
                     ),

        html.Div(),
        html.Div(id='output_container_4', children=[]),
        html.Div(),
        html.Br(),
        dcc.Graph(id='my_mobileDNA_map_4', figure={}),
        html.Br(),
        html.Br()

    ])

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

    # Plotly Express
    fig = px.pie(
        data_frame=dff,
        values='duration',
        names='category',
        title='screen time per category',
        color_discrete_sequence=px.colors.sequential.Blues,
        template='seaborn',
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')

    return container, fig

@app.callback(
    [Output(component_id='output_container_2', component_property='children'),
     Output(component_id='my_mobileDNA_map_2', component_property='figure')],
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
        template='seaborn',
        color_discrete_sequence=px.colors.sequential.Blues,
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')

    return container, fig

@app.callback(
    [Output(component_id='output_container_3', component_property='children'),
     Output(component_id='my_mobileDNA_map_3', component_property='figure')],
    [Input(component_id='slct_id_3', component_property='value'),
     Input(component_id='slct_category', component_property='value')]
)

def update_graph(selected_id, selected_cat):

    container = "screentime in '{}' category for user with id: {}".format(selected_cat, selected_id)

    dff = df.copy()
    dff['duration'] = (dff['duration'] / 60)
    dff = dff[dff["id"] == selected_id]
    dff = dff[dff["category"] == selected_cat]

    dff = dff.groupby(['startDate', 'category'])['duration'].agg(duration='sum')
    dff.reset_index(inplace=True)

    # Plotly Express
    fig = px.bar(
        data_frame=dff,
        x='startDate',
        y='duration',
        color='duration',
        color_continuous_scale=px.colors.sequential.Blues,
        labels={'duration': 'duration (min)', 'startDate': 'date'},
        template='seaborn',
    )

    return container, fig


@app.callback(
    [Output(component_id='output_container_4', component_property='children'),
     Output(component_id='my_mobileDNA_map_4', component_property='figure')],
    [Input(component_id='slct_tod', component_property='value')]
)

def update_graph(option_slctd):
    dff = df.copy()
    dff = dff[dff["startTOD"] == option_slctd]

    container = ""

    # Plotly Express
    fig = px.scatter_mapbox(
        dff,
        lat='latitude',
        lon='longitude',
        zoom=5,
        mapbox_style='carto-positron',  # styles: carto-darkmatter, carto-positron, open-street-map, stamen-terrain, stamen-toner, stamen-watercolor, white-bg
        template='seaborn',
        hover_data=['id'],
    )

    fig.update_layout(
        margin=dict(l=300, r=300, t=20, b=20),
        hovermode='closest',
        mapbox=dict(
            bearing=0,
            center=go.layout.mapbox.Center(
                lat=50.72,
                lon=4.43
            ),
            pitch=0,
            zoom=6
        )
    )

    return container, fig

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)
