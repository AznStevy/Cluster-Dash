# Cluster-Dash
Dashboard for C. elegan cell organization and clustering
![Dashboard Image](https://i.imgur.com/WdENqpa.png)

# Installing components
If you are using an Anaconda distribution of Python, make sure you do `conda install -c plotly plotly=4.5.4` and `conda install -c conda-forge dash`. This installs the necessary components of the dashboard from Plotly.

# Running
At the top, you'll see the variables for `vol_prev` and `vol_curr`. You can set these to whatever you like given that those worm volumes have been straightened. By default, they are something like:
```
vol_prev = 7
vol_curr = vol_prev + 1
```
If you don't wish to edit the functions that define the file structure, shown here:
```
def folder_name(vol_num): return 'straightened_test_data\\Decon_reg_{}\\Decon_reg_{}_results\\'.format(
    vol_num, vol_num)


def lattice_file(vol_num): return folder_name(vol_num) + \
    'straightened_named_seamcells\\straightened_seamcells.csv'


def annotation_file(vol_num): return folder_name(
    vol_num) + 'straightened_annotations\\straightened_annotations.csv'
```
You can simply drag your `decon_reg_#` folder into the `straightened_test_data` folder and run the program that way. They will all output in the `output` folder.

# Operating the dashboard
The code will automatically generate clusters and try to match them by distance. If you are not happy with an assignment, you can filter on the respect table using the top row (e.g. type in `n40`) and then change the cluster number. You may need to drag your window/change your window position for changes to take effect (not sure why this is/it's a bug). If you want to unsync the plots, hit the `Unsync Plots` button at the bottom and again to sync them. To create the output csvs, hit the `Output CSVs` button. As said previously, the output will be in the `output` folder.
