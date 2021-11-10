import pandas as pd

import plotly.express as px  # (version 4.7.0 or higher)
import plotly.graph_objects as go

from dash import Dash, dcc, html, Input, Output  # pip install dash (version 2.0.0 or higher)

from mobiledna.core.appevents import Appevents
from datetime import date

app = Dash(__name__)

# mapbox toke
mapbox_access_token = "pk.eyJ1Ijoic3Blcm5lZWwiLCJhIjoiY2t2dGtlNWQ5MjRmMzJ3cWhhaWpzN2w5cyJ9.DakJIN8BzZ-JxaQpS1cVkA"

# -- Import and clean data (importing csv into pandas)
ae = Appevents.load_data('data_qa.csv', sep=';')
df = ae.__data__
pd.set_option('display.max_columns', None)
df['duration'] = df['duration'] / 60
print(df.head())



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

        dcc.DatePickerRange(
            id='my-date-picker-range',
            start_date=date(2021,6,1),
            end_date=date(2021,10,28),
            display_format='DD/MM/YYYY',
            start_date_placeholder_text='Pick a date',
            style={'text-align':'center'},
        ),

        html.Br(),

        dcc.Dropdown(
            id="slct_tod",
            options=[{"label": x, "value": x} for x in tods],
            multi=False,
            placeholder="Set a time of the day",
            value=tods[0],
            style={'width': "40%"}
        ),

        html.Div(),
        html.Div(id='output_container_4', children=[]),
        html.Div(),
        html.Br(),
        dcc.Graph(id='my_mobileDNA_map_4', figure={}),
        html.Br(),
        html.Br()

    ]),

    html.Div([
        html.Br(), html.Br(), html.Br(), html.Br(), html.Br(), html.Br()
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

    container = ""

    dff = df.copy()
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
    fig.update_layout(title_text=f'usage for user with id: {option_slctd}', title_x=0.5)

    return container, fig

@app.callback(
    [Output(component_id='output_container_2', component_property='children'),
     Output(component_id='my_mobileDNA_map_2', component_property='figure')],
    [Input(component_id='slct_id_2', component_property='value')]
)
def update_graph(option_slctd):

    container = ""
    dff = df.copy()
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
    fig.update_layout(title_text=f'usage for user with id: {option_slctd}', title_x=0.5)

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
    [Input(component_id='slct_tod', component_property='value'),
     Input('my-date-picker-range', 'start_date'),
     Input('my-date-picker-range', 'end_date')]
)

def update_graph(option_slctd, start_date, end_date):
    dff = df.copy()
    print(start_date)
    dff = dff[dff["startTOD"] == option_slctd]
    dff = dff[dff["startDate"] >= start_date]
    dff = dff[dff["endDate"] <= end_date]
    print(dff.head())


    container = ""

    # Plotly Express
    fig = px.density_mapbox(
        dff,
        lat='latitude',
        lon='longitude',
        z='duration',
        zoom=5,
        radius=10,
        mapbox_style='light',  # styles: carto-darkmatter, carto-positron, open-street-map, stamen-terrain, stamen-toner, stamen-watercolor, white-bg
        template='seaborn',
        hover_data=['id'],
    )

    fig.update_layout(
        margin=dict(l=300, r=300, t=20, b=20),
        hovermode='closest',
        mapbox=dict(
            accesstoken=mapbox_access_token,
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
