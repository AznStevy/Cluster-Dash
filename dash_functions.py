import string
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.cluster import AgglomerativeClustering
from sklearn.neighbors.nearest_centroid import NearestCentroid

colors = {
    'background': '#111111',
    'text': '#FFF',
    'seam': 'rgb(125,125,125)',
    'mesh_opacity': .15
}
coord_labels = ['x_voxels', 'y_voxels', 'z_voxels']


def order_seam_cell_table(seam_cell_table):
    cell_names = np.array(['H0L', 'H0R', 'H1L', 'H1R', 'H2L', 'H2R', 'V1L', 'V1R', 'V2L',
                           'V2R', 'V3L', 'V3R', 'V4L', 'V4R', 'V5L', 'V5R', 'V6L', 'V6R', 'TL', 'TR'])

    index_col = []
    last_cell_idx = 0
    for row_idx, row in seam_cell_table.iterrows():
        cell_name = row['name']
        cell_idx = np.argwhere(cell_name == cell_names)

        if cell_idx:
            index_col.append(cell_idx)
        else:
            cell_idx = (np.ceil(last_cell_idx + 0.0001) - last_cell_idx)/2
            index_col.append(cell_idx)

    seam_cell_table['true_index'] = tuple(index_col)
    seam_cell_table = seam_cell_table.sort_values(by=['true_index'])
    return seam_cell_table


def get_lattice_mat(num_seam_cells):
    adj_mat = np.zeros((num_seam_cells, num_seam_cells))

    for i in range(num_seam_cells):
        if i >= num_seam_cells - 2:  # hand end case
            adj_mat[i, i-2] = 1
            adj_mat[i-2, i] = 1
            if i == num_seam_cells - 2:  # second to last cell
                adj_mat[i, i+1] = 1
                adj_mat[i+1, i] = 1
            else:  # last cell
                adj_mat[i, i-1] = 1
                adj_mat[i-1, i] = 1
        elif i % 2 == 0:  # if even
            adj_mat[i+1, i] = 1
            adj_mat[i+2, i] = 1
            adj_mat[i, i+1] = 1
            adj_mat[i, i+2] = 1
        elif i % 2 == 1:  # if odd
            adj_mat[i-1, i] = 1
            adj_mat[i+2, i] = 1
            adj_mat[i, i-1] = 1
            adj_mat[i, i+2] = 1

    return adj_mat


def create_edge_connections(adj_mat, coords):
    # a list of edge connections

    all_connections = []
    for row_idx in range(adj_mat.shape[0]):  # from node
        connections = []
        for col_idx in range(adj_mat.shape[1]):  # to node
            if adj_mat[row_idx, col_idx] == 1:
                connections.append((row_idx, col_idx))
        all_connections.extend(connections)

    Xe, Ye, Ze = ([], [], [])
    for e in all_connections:
        # x-coordinates of edge ends
        Xe += [coords[e[0]][0], coords[e[1]][0], None]
        Ye += [coords[e[0]][1], coords[e[1]][1], None]
        Ze += [coords[e[0]][2], coords[e[1]][2], None]

    return Xe, Ye, Ze

# generate individual coords for alpha hull/triangulation


def by_region(full_cell_table):
    coords = full_cell_table[coord_labels].to_numpy()
    labels = full_cell_table['cluster'].to_numpy()

    triangle_region = {}
    for cell_idx, region_id in enumerate(labels):
        if str(region_id) not in triangle_region.keys():
            triangle_region[region_id] = []

        triangle_region[region_id].append(coords[cell_idx, :].tolist())

    # change all into numpy arrays
    for region in triangle_region.keys():
        triangle_region[region] = np.array(triangle_region[region])

    return triangle_region


def linear_assignment(coords, pot_coords):
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist

    # Solve linear assignment problem
    costs = cdist(coords, pot_coords)
    [r, c] = linear_sum_assignment(costs)

    return c


def find_centroids(coords, labels):
    """Find centroids"""
    clf = NearestCentroid()
    clf.fit(coords, labels)
    centroids = clf.centroids_
    ids = clf.classes_
    return centroids, ids


# maps previous to current
def generate_plot_labels(prev_coords, model_prev, curr_coords, model_curr):
    prev_cluster_centroids, prev_cluster_ids = find_centroids(
        prev_coords, model_prev.labels_)
    curr_cluster_centroids, curr_cluster_ids = find_centroids(
        curr_coords, model_curr.labels_)

    cluster_match = linear_assignment(
        prev_cluster_centroids, curr_cluster_centroids)
    prev_curr_map = {k: v for v, k in enumerate(
        curr_cluster_ids[cluster_match])}
    new_curr_model = []
    for label in model_curr.labels_:
        new_curr_model.append(prev_curr_map[label])
    new_curr_model = np.array(new_curr_model)

    # reorder based on position in plot
    ordered_idxs = np.argsort(prev_cluster_centroids[:, 2])
    old_to_ordered = {k: v for v, k in enumerate(ordered_idxs)}

    # order both old and new
    prev_ordered = []
    for label in model_prev.labels_:
        prev_ordered.append(old_to_ordered[label])
    prev_ordered = np.array(prev_ordered)

    curr_ordered = []
    for label in new_curr_model:
        curr_ordered.append(old_to_ordered[label])
    curr_ordered = np.array(curr_ordered)

    return prev_ordered.astype(str), curr_ordered.astype(str)


def create_sub_ids(full_cell_table):
    # append a cluster sub ID
    sub_id = []
    counter = {}
    for row_idx, cell_info in full_cell_table.iterrows():
        cell_cluster = str(cell_info['cluster'])

        if cell_cluster not in counter.keys():
            counter[cell_cluster] = 0

        sub_id.append(str(counter[cell_cluster]))
        counter[cell_cluster] += 1
    return np.array(sub_id)


def create_complete_plot(full_cell_table, full_seam_table, edges, regions):
    data = []
    data.append(create_seam_plot(full_seam_table))
    data.append(create_lattice_plot(edges))
    data.append(create_cell_scatter(full_cell_table))
    data.extend(create_meshes(regions))
    return data


def create_seam_plot(full_seam_table):
    seam_coords = full_seam_table[coord_labels].to_numpy()
    return dict(
        x=seam_coords[:, 0],
        y=seam_coords[:, 2],
        z=seam_coords[:, 1],
        mode='markers+text',
        text=full_seam_table['name'],
        name="Seam cells",
        textfont=dict(
            size=20,
            color=colors['seam']
        ),
        type='scatter3d',
    )


def create_lattice_plot(edges):
    return dict(
        x=edges[0],
        y=edges[2],
        z=edges[1],
        mode='lines',
        line=dict(color=colors['seam'], width=10),
        hoverinfo='none',
        type='scatter3d',
    )


def create_cell_scatter(full_table):
    return dict(
        x=full_table['x_voxels'],
        y=full_table['z_voxels'],
        z=full_table['y_voxels'],
        name=full_table['cluster'],
        mode='markers+text',
        text=["{}({}-{})".format(
            name, full_table['cluster'].iloc[cell_idx],
            full_table['sub_id'].iloc[cell_idx])
            for cell_idx, name in enumerate(full_table['name'].to_numpy())],
        marker=dict(size=14, color=full_table['cluster']),
        textfont=dict(
            size=12,
            color=colors['text']
        ),
        color_continuous_scale='Viridis',
        colorscale='Viridis',
        type='scatter3d'
    )


def create_meshes(regions):
    meshes = []
    for region in regions.keys():
        simplexes = go.Mesh3d(
            alphahull=.15,
            name='',
            x=regions[region][:, 0],
            y=regions[region][:, 2],
            z=regions[region][:, 1],
            color='#90EE90',  # set the color of simplexes in alpha shape
            opacity=colors['mesh_opacity'],
            hoverinfo='none'
        )
        meshes.append(simplexes)
    return meshes


def create_annotation_output(full_table):
    output_labels = ['name']
    output_labels.extend(coord_labels)
    output_labels.extend(['R', 'G', 'B'])

    output_table = full_table[output_labels].copy(deep=True)

    # generate new names
    new_names = []
    for row_idx, row in full_table.iterrows():
        cluster_letter = string.ascii_uppercase[int(row['cluster'])]
        cluster_number = str(row['sub_id'])

        cell_id = cluster_letter + cluster_number
        new_names.append(cell_id)

    output_table['name'] = tuple(new_names)
    return output_table
