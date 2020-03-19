# import libararies
import os
import json
import dash
import numpy as np
import pandas as pd
from dash_functions import *

import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

# define folder structure --------------------------------------------------------------------


def folder_name(vol_num): return 'straightened_test_data\\Decon_reg_{}\\Decon_reg_{}_results\\'.format(
    vol_num, vol_num)


def lattice_file(vol_num): return folder_name(vol_num) + \
    'straightened_named_seamcells\\straightened_seamcells.csv'


def annotation_file(vol_num): return folder_name(
    vol_num) + 'straightened_annotations\\straightened_annotations.csv'


# Grab data ------------------------------------------------------------------------------------
vol_prev = 45
vol_curr = vol_prev + 1

coord_labels = ['x_voxels', 'y_voxels', 'z_voxels']

global prev_full_seam_table
global curr_full_seam_table
global prev_full_cell_table
global curr_full_cell_table

# get seam files
prev_seam_file = lattice_file(vol_prev)
curr_seam_file = lattice_file(vol_curr)
prev_full_seam_table = pd.read_csv(prev_seam_file)
curr_full_seam_table = pd.read_csv(curr_seam_file)
# get annotation files
prev_annotation_file = annotation_file(vol_prev)
curr_annotation_file = annotation_file(vol_curr)
prev_full_cell_table = pd.read_csv(prev_annotation_file)
curr_full_cell_table = pd.read_csv(curr_annotation_file)

adj_mat_curr = get_lattice_mat(curr_full_seam_table.shape[0])
adj_mat_prev = get_lattice_mat(prev_full_seam_table.shape[0])
edges_curr = create_edge_connections(adj_mat_curr,
                                     curr_full_seam_table[coord_labels].to_numpy())
edges_prev = create_edge_connections(adj_mat_prev,
                                     prev_full_seam_table[coord_labels].to_numpy())

# determine clusters in each plot
model_prev = AgglomerativeClustering(linkage='ward', n_clusters=26)
model_prev.fit(prev_full_cell_table[coord_labels].to_numpy())
model_curr = AgglomerativeClustering(linkage='ward', n_clusters=26)
model_curr.fit(curr_full_cell_table[coord_labels].to_numpy())

# attempt to match clusters and order them from head to tail
prev_ordered, curr_ordered = generate_plot_labels(
    prev_full_cell_table[coord_labels].to_numpy(), model_prev,
    curr_full_cell_table[coord_labels].to_numpy(), model_curr)

# append these to the tables ---------------------------------------------
prev_full_cell_table['cluster'] = prev_ordered
curr_full_cell_table['cluster'] = curr_ordered
prev_regions = by_region(prev_full_cell_table)
curr_regions = by_region(curr_full_cell_table)
prev_full_cell_table['sub_id'] = create_sub_ids(prev_full_cell_table)
curr_full_cell_table['sub_id'] = create_sub_ids(curr_full_cell_table)

# app layout --------------------------------------------------------------

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


prev_data = create_complete_plot(
    prev_full_cell_table, prev_full_seam_table,
    edges_prev, prev_regions)
curr_data = create_complete_plot(
    curr_full_cell_table, curr_full_seam_table,
    edges_curr, curr_regions)

layout = {
    'template': "plotly_dark",
    'scene': {
        'aspectmode': 'data',
        'xaxis': {
            'showgrid': False,
        },
        'yaxis': {
            'showgrid': False
        },
        'zaxis': {
            'showgrid': False
        },
        "camera": {
            "up": {
                "x": 0,
                "y": 0,
                "z": 1
            },
            "center": {
                "x": 0,
                "y": 0,
                "z": 0
            },
            "eye": {
                "x": 2,
                "y": 0,
                "z": 0.5
            },
            "projection": {
                "type": "perspective"
            }
        }
    },
    'showlegend': False,
    'margin': {'l': 0, 'r': 0, 'b': 0, 't': 0},
    'clickmode': 'event+select',
    'plot_bgcolor': colors['background'],
    'paper_bgcolor': colors['background']
}

app.layout = html.Div([
    html.Div(className='row', children=[
        html.Div(className='ten columns', children=[
            dcc.Graph(
                id='prev_plot',
                figure={
                    'data': prev_data,
                    'layout': layout
                }
            )]
        ),
        html.Div(className='two columns', children=[
            dash_table.DataTable(
                id='prev_table',
                columns=[
                    {"name": i, "id": i, "deletable": False, "selectable": False} for i in ['name', 'cluster', 'sub_id']
                ],
                data=prev_full_cell_table.to_dict('records'),
                editable=True,
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                page_action="native",
                page_current=0,
                page_size=10,
            )]
        )
    ]),
    html.Div(className='row', children=[
        html.Div(className='ten columns', children=[
            dcc.Graph(
                id='curr_plot',
                figure={
                    'data': curr_data,
                    'layout': layout
                }
            )]
        ),
        html.Div(className='two columns', children=[
            dash_table.DataTable(
                id='curr_table',
                columns=[
                    {"name": i, "id": i, "deletable": False, "selectable": False} for i in ['name', 'cluster', 'sub_id']
                ],
                data=curr_full_cell_table.to_dict('records'),
                editable=True,
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                page_action="native",
                page_current=0,
                page_size=10,
            )]
        )
    ]),
    html.Div(children=[
        html.Button('Output CSVs',
                    id='output-button'),
        html.P(id='placeholder')
    ])
])


# app callbacks ------


@app.callback(
    [
        Output('prev_plot', 'figure'),
        Output('prev_table', 'data'),
    ],
    [
        Input('curr_plot', 'relayoutData'),
        Input('prev_table', 'columns')
    ],
    [
        State('prev_table', 'data'),
    ])
def update_prev(camera_angle, columns, rows):
    # updating table values
    new_data = pd.DataFrame(rows, columns=[c['name'] for c in columns])
    new_clusters = new_data['cluster'].to_numpy().astype(str)
    prev_full_cell_table['cluster'] = tuple(new_clusters)

    # regerate regions
    prev_regions = by_region(prev_full_cell_table)
    sub_ids = np.array(create_sub_ids(prev_full_cell_table)).astype(str)
    prev_full_cell_table['sub_id'] = tuple(sub_ids)

    # re-create plot
    prev_data = create_complete_plot(
        prev_full_cell_table, prev_full_seam_table,
        edges_prev, prev_regions)

    # updating camera angle
    updated_layout = layout
    try:
        updated_layout['scene']['camera'] = camera_angle['scene.camera']
    except:
        pass

    # update data table
    for row_idx, row in enumerate(rows):
        row['cluster'] = new_clusters[row_idx]
        row['sub_id'] = sub_ids[row_idx]

    # create updated figure
    updated_figure = {
        'data': prev_data,
        'layout': updated_layout
    }

    return [updated_figure, rows]


@app.callback(
    [
        Output('curr_plot', 'figure'),
        Output('curr_table', 'data')],
    [
        Input('prev_plot', 'relayoutData'),
        Input('curr_table', 'columns')
    ],
    [
        State('curr_table', 'data'),
    ])
def update_curr(camera_angle, columns, rows):
    # updating table values
    new_data = pd.DataFrame(rows, columns=[c['name'] for c in columns])
    new_clusters = new_data['cluster'].to_numpy().astype(str)
    curr_full_cell_table['cluster'] = tuple(new_clusters)

    # regerate regions
    curr_regions = by_region(curr_full_cell_table)
    sub_ids = np.array(create_sub_ids(curr_full_cell_table)).astype(str)
    curr_full_cell_table['sub_id'] = tuple(sub_ids)

    # re-create plot
    new_curr_data = create_complete_plot(
        curr_full_cell_table, curr_full_seam_table,
        edges_curr, curr_regions)

    # updating camera angle
    updated_layout = layout
    try:
        updated_layout['scene']['camera'] = camera_angle['scene.camera']
    except:
        pass

    # update data table
    for row_idx, row in enumerate(rows):
        row['cluster'] = str(new_clusters[row_idx])
        row['sub_id'] = str(sub_ids[row_idx])

    # create updated figure
    updated_figure = {
        'data': new_curr_data,
        'layout': updated_layout
    }

    return [updated_figure, rows]


@app.callback(
    Output('placeholder', 'children'),
    [Input('output-button', 'n_clicks')]
)
def on_save_press(n_clicks):
    output_folder = 'output'
    if not os.path.isdir(output_folder):
        os.mkdir(output_folder)

    prev_output_table = create_annotation_output(prev_full_cell_table)
    curr_output_table = create_annotation_output(curr_full_cell_table)

    prev_filename = '{}\straightened_annotations_{}.csv'.format(
        output_folder, vol_prev)
    curr_filename = '{}\straightened_annotations_{}.csv'.format(
        output_folder, vol_curr)

    # save files
    prev_output_table.to_csv(prev_filename, index=False)
    curr_output_table.to_csv(curr_filename, index=False)

    return []


if __name__ == '__main__':
    app.run_server(debug=True)
