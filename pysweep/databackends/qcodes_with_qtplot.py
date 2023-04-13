import numpy as np
import time
import os

try:
    import ipywidgets as ipw
    from IPython.display import display
except:
    print('Ipywidgets not loaded!')

import qcodes as qc
from qcodes.plots.pyqtgraph import QtPlot
from qcodes.dataset.measurements import Measurement

from pysweep.databackends.base import DataParameter, DataParameterFixedSweep, DataParameterFixedAxis
from pytopo.qctools.dataset2 import select_experiment
import pysweep.databackends.base as base

import pysweep.databackends.qcodes as qcodes_backend

'''
A subclassed qcodes DataBackend, that makes live plots
of 1D and 2D data.
For higher dimentionality use ordinary qcodes DataBackend.
'''


class DataBackend(qcodes_backend.DataBackend):
    def __init__(self, experiment_name, sample, station,
                    plotting_interval: float=3,
                    export_png=True,
                    progress_bar=False,
                    close_when_finished=False):
        '''
        This is a PycQED-inspired subclass of qcodes data backend
        that adds 1D and 2D live plotting functionality.

        The backend uses QtPlot from QCoDeS for live plotting. Since plotting
        runs in the same thread as the measurement it introduces an overhead
        that comes from opening of the windows with plots and updating them.
        With plotting_interval=3 (seconds) overhead in measurement
        is relatively small (~10%).

        The backend has an option of outputting a PNG image at the end
        of the measurement. The figures are saved in subdirectories
        of the folder where database is saved.

        Plots titles contain information allowing to easily identify
        which database the data was saved in and where in the database
        the data is saved.

        At this time only 1D and 2D datasets and only point-by-point
        measurements are supported. 2D datasets will show correctly
        only if they are on a regular grid.
        Increasing generality is on TODO list.
        '''

        self.plotting_interval = plotting_interval
        self.export_png = export_png
        self.progress_bar = progress_bar
        self.close_when_finished = close_when_finished

        self.experiment = select_experiment(experiment_name, sample)
        measurement = Measurement(self.experiment, station)

        super().__init__(measurement)

    def setup(self, paramstructure, dict_waterfall):
        super().setup(paramstructure, dict_waterfall)
        
        # distinguish between independent and dependent parameters
        # (coordinates and quantities, respectively)
        self.soft_sweeped_coordinates = []
        self.hard_sweeped_coordinates = []
        self.quantities = []

        parameter_index = 0
        for param in paramstructure:
            if isinstance(param, DataParameterFixedAxis):
                if ('None' in param.name) and (param.unit is 'e'):
                    parameter_index += 1
                    continue
                self.hard_sweeped_coordinates.append({'name': param.name,
                                                 'unit': param.unit,
                                                 'coordinates': param.coordinates,
                                                 'independent': param.independent})
            elif isinstance(param, DataParameterFixedSweep):
                if ('None' in param.name) and (param.unit is 'e'):
                    parameter_index += 1
                    continue
                self.soft_sweeped_coordinates.append({'name': param.name,
                                                 'unit': param.unit,
                                                 'start': param.start,
                                                 'end': param.stop,
                                                 'size': param.npoints,
                                                 'independent': param.independent})
            else:
                self.quantities.append({'name': param.name,
                                     'unit': param.unit,
                                     'type': param.paramtype,
                                     'index': parameter_index,
                                     'extra_dependencies': param.extra_dependencies})

            parameter_index += 1


        # to account for the parameter of
        # the innermost loop stored in the last column
        self.soft_sweeped_coordinates.reverse()
        self.hard_sweeped_coordinates.reverse()

        self.create_plots()

        if self.progress_bar:
            self.create_progress_bar()

    def __enter__(self):
        super().__enter__()

        # read database name and identifiers allowing
        # to locate the dataset in the database
        exp_name = self.runner.ds.exp_name
        run_id = self.runner.ds.run_id
        db_name = self.runner.ds.path_to_db.split('\\')[-1].split('.')[0]
        timestamp = self.runner.ds.run_timestamp()
        self.time = timestamp.split(' ')[1].replace(':','-')

        # add titles to plots
        for i, quantity in enumerate(self.quantities):
            title_list = []
            title_list.append(quantity['name'])
            # title_list.append(exp_name)
            title_list.append(str(run_id))
            title_list.append(db_name)
            title_list.append(timestamp)

            plot_title = ', '.join(title_list)
            quantity['plot'].subplots[0].setTitle(plot_title,
                            size='7pt',color='000000')

        # create a directory for figures
        if self.export_png:
            fmt = '.'.join(self.runner.ds.path_to_db.split('.')[:-1])
            fmt = fmt+'\\{date}\\{time}'
            fmt = fmt.replace('\\', '/')
            try:
                self.io = qc.DiskIO('.')
            except AttributeError:
                self.io = qc.data.DiskIO('.')
            loc_provider = qc.data.location.FormatLocation(
                fmt=fmt)
            self.directory_prefix = loc_provider(self.io)
            self.directory_prefix = '/'.join(self.directory_prefix.split('/')[:-1])
            print(self.directory_prefix )
            try:
                os.makedirs(self.directory_prefix)
            except FileExistsError:
                pass

        # a counter used to select where the new data point
        # should be inserted
        self.point_counter = 0
        # initialize timer for live update
        self.last_update_time = time.time()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)

        # at the end update the plots for the last time
        # and export figures
        for qi, quantity in enumerate(self.quantities):
            quantity['plot'].update_plot()
            if self.progress_bar:
                self.update_progress_bar()

            if self.export_png:
                run_id = self.runner.ds.run_id
                filename = '/'.join([self.directory_prefix,
                                str(run_id)+'_'+self.time+'_'+quantity['name']+'.png'])
                quantity['plot'].save(filename=filename)

            if self.close_when_finished:
                quantity['plot'].win.close()
                del quantity['plot']


    def add_to_line(self, line):
        super().add_to_line(line)       

        for qi, quantity in enumerate(self.quantities):
            # case for the measured data that is returned point-by-point
            if quantity['type'] == 'numeric':
                # 1D measurement
                if len(self.soft_sweeped_coordinates) == 1:
                    quantity['xvals'][self.point_counter] = line[2][1]
                    quantity['yvals'][self.point_counter] = line[quantity['index']][1]
                elif len(self.soft_sweeped_coordinates) == 2:
                    x_index = self.point_counter % self.soft_sweeped_coordinates[0]['size']
                    y_index = int((self.point_counter - x_index)/self.soft_sweeped_coordinates[0]['size'])

                    # commented out because I can't get the irregular grid
                    # to work [FKM], TODO
                    # quantity['xvals'][y_index] = line[1][1]
                    # quantity['yvals'][x_index] = line[2][1]
                    quantity['zvals'][y_index,x_index] = line[quantity['index']][1]
            # case for the measured data that is returned line-by-line
            elif quantity['type'] == 'array':
                # 1D measurement
                if len(self.soft_sweeped_coordinates) == 0:
                    quantity['yvals'][:] = line[quantity['index']][1][:]
                # 2D measurement
                elif len(self.soft_sweeped_coordinates) == 1:
                    quantity['zvals'][:,self.point_counter] = line[quantity['index']][1][:]
            else:
                raise NotImplementedError('qcodes_with_qtplot only supports plotting 1D and 2D data')
        
        # update plot only every several (self.plotting_interval)
        # seconds to minimize the overhead
        if time.time()-self.last_update_time > self.plotting_interval:
            for qi, quantity in enumerate(self.quantities):
                quantity['plot'].update_plot()
            if self.progress_bar:
                self.update_progress_bar()
            self.last_update_time = time.time()

        self.point_counter += 1

    def create_plots(self):
        # open each measured quantity in a separate window
        # this allows the user to keep only the "interesting"
        # dataset opened

        # print(self.quantities)
        # print(self.soft_sweeped_coordinates)
        for i, quantity in enumerate(self.quantities):
            quantity['plot'] = QtPlot(window_title=quantity['name'],
                        figsize=(570, 450),
                        fig_x_position=int(i/2)*0.3,
                        fig_y_position=(i%2)*0.33)

            # case for the measured data that is returned point-by-point
            if quantity['type'] == 'numeric':
                # 1D measurement
                if len(self.soft_sweeped_coordinates) == 1:
                    coordinate = self.soft_sweeped_coordinates[0]

                    quantity['xvals'] = np.linspace(coordinate['start'],
                                        coordinate['end'],
                                        coordinate['size'])
                    quantity['yvals'] = np.ones(coordinate['size'])
                    quantity['yvals'][:] = np.NaN

                    quantity['plot'].add(x=quantity['xvals'],
                                         y=quantity['yvals'],
                                         xlabel=coordinate['name'],
                                         xunit=coordinate['unit'],
                                         ylabel=quantity['name'],
                                         yunit=quantity['unit'])

                # 2D measurement
                elif len(self.soft_sweeped_coordinates) == 2:
                    coordinateX = self.soft_sweeped_coordinates[0]
                    coordinateY = self.soft_sweeped_coordinates[1]

                    quantity['xvals'] = np.linspace(coordinateX['start'],
                                        coordinateX['end'],
                                        coordinateX['size'])
                    quantity['yvals'] = np.linspace(coordinateY['start'],
                                        coordinateY['end'],
                                        coordinateY['size'])

                    quantity['zvals'] = np.ones([coordinateY['size'],
                                                 coordinateX['size']])
                    quantity['zvals'][:,:] = np.NaN

                    quantity['plot'].add(x=quantity['xvals'],
                                         y=quantity['yvals'],
                                         z=quantity['zvals'],
                                         xlabel=coordinateX['name'],
                                         xunit=coordinateX['unit'],
                                         ylabel=coordinateY['name'],
                                         yunit=coordinateY['unit'],
                                         zlabel=quantity['name'],
                                         zunit=quantity['unit'])
                else:
                    raise NotImplementedError('qcodes_with_qtplot only'
                                'supports plotting 1D and 2D data')

            # case for the measured data that is returned line-by-line
            elif quantity['type'] == 'array':
                # 1D measurement

                if len(self.soft_sweeped_coordinates) == 0:
                    # check if you should use the default dependency
                    # on hard_sweeped coordinate, otherwise find a hard_sweeped
                    # coordinate with a matching name
                    if quantity['extra_dependencies'] == []:
                        coordinate = self.hard_sweeped_coordinates[0]
                    else:
                        for coordinate in self.hard_sweeped_coordinates:
                            if coordinate['name'] == quantity['extra_dependencies'][0]:
                                break

                    quantity['xvals'] = coordinate['coordinates']
                    quantity['yvals'] = np.ones(coordinate['coordinates'].shape)
                    quantity['yvals'][:] = np.NaN

                    quantity['plot'].add(x=quantity['xvals'],
                                         y=quantity['yvals'],
                                         xlabel=coordinate['name'],
                                         xunit=coordinate['unit'],
                                         ylabel=quantity['name'],
                                         yunit=quantity['unit'])
                # 2D measurement
                elif len(self.soft_sweeped_coordinates) == 1:
                    coordinateX = self.soft_sweeped_coordinates[0]
                    # check if you should use the default dependency
                    # on hard_sweeped coordinate, otherwise find a hard_sweeped
                    # coordinate with a matching name
                    if quantity['extra_dependencies'] == []:
                        coordinateY = self.hard_sweeped_coordinates[0]
                    else:
                        for coordinateY in self.hard_sweeped_coordinates:
                            if coordinateY['name'] == quantity['extra_dependencies'][0]:
                                break

                    quantity['xvals'] = np.linspace(coordinateX['start'],
                                        coordinateX['end'],
                                        coordinateX['size'])
                    quantity['yvals'] = coordinateY['coordinates']

                    quantity['zvals'] = np.ones([coordinateY['coordinates'].shape[0],
                                                 coordinateX['size']])
                    quantity['zvals'][:,:] = np.NaN

                    quantity['plot'].add(x=quantity['xvals'],
                                         y=quantity['yvals'],
                                         z=quantity['zvals'],
                                         xlabel=coordinateX['name'],
                                         xunit=coordinateX['unit'],
                                         ylabel=coordinateY['name'],
                                         yunit=coordinateY['unit'],
                                         zlabel=quantity['name'],
                                         zunit=quantity['unit'])
                else:
                    raise NotImplementedError('qcodes_with_qtplot only'
                                'supports plotting 1D and 2D data')
                    
            else:
                raise NotImplementedError('Unsupported type of data.'
                                    ' Must be "numeric" of "array".')

    def create_progress_bar(self):
        first_quantity = self.quantities[0]
        if 'zvals' in first_quantity.keys():
            total_datapoints = np.product(first_quantity['zvals'].shape)
        else:
            total_datapoints = first_quantity['yvals'].shape[0]
        self.progress_bar = ipw.FloatProgress(value=0,
                                        min=0, max=total_datapoints,
                                        description='Progress:')
        display(self.progress_bar)

    def update_progress_bar(self):
        self.progress_bar.value = self.point_counter
