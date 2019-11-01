import numpy as np
import time
import os

import qcodes as qc
from qcodes.plots.pyqtgraph import QtPlot
from qcodes.dataset.measurements import Measurement

from pysweep.databackends.base import DataParameter, DataParameterFixedSweep
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
                    plotting_interval: float=3, export_png=True):
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

        self.experiment = select_experiment(experiment_name, sample)
        measurement = Measurement(self.experiment, station)

        super().__init__(measurement)

    def setup(self, paramstructure):
        super().setup(paramstructure)  
        
        # distinguish between independent and dependent parameters
        # (coordinates and quantities, respectively)
        self.coordinates = []
        self.quantities = []

        for param in paramstructure:
            if isinstance(param, DataParameterFixedSweep):
                if ('None' in param.name) and (param.unit is 'e'):
                    continue
                self.coordinates.append({'name': param.name,
                                     'unit': param.unit,
                                     'start': param.start,
                                     'end': param.stop,
                                     'size': param.npoints})
            else:
                self.quantities.append({'name': param.name,
                                     'unit': param.unit,
                                     'type': 'value'})

        # to account for the parameter of
        # the innermost loop stored in the last column
        self.coordinates.reverse()

        self.create_plots()

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
            title_list.append(exp_name)
            title_list.append(str(run_id))
            title_list.append(db_name)
            title_list.append(timestamp)

            plot_title = ', '.join(title_list)
            quantity['plot'].subplots[0].setTitle(plot_title,
                            size='7pt',color='000000')

        # create a directory for figures
        if self.export_png:
            fmt = self.runner.ds.path_to_db.split('.')[0]
            fmt = fmt+'\\{date}\\{time}'
            fmt = fmt.replace('\\', '/')
            self.io = qc.DiskIO('.')
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

            if self.export_png:
                filename = '/'.join([self.directory_prefix,
                                self.time+'_'+quantity['name']+'.png'])
                quantity['plot'].save(filename=filename)

    def add_to_line(self, line):
        super().add_to_line(line)

        if len(self.coordinates) == 1:
            for qi, quantity in enumerate(self.quantities):
                quantity['xvals'][self.point_counter] = line[2][1]
                quantity['yvals'][self.point_counter] = line[3+qi][1]
        elif len(self.coordinates) == 2:
            for qi, quantity in enumerate(self.quantities):
                x_index = self.point_counter % self.coordinates[0]['size']
                y_index = int((self.point_counter - x_index)/self.coordinates[0]['size'])

                # commented out because I can't get the irregular grid
                # to work [FKM], TODO
                # quantity['xvals'][y_index] = line[1][1]
                # quantity['yvals'][x_index] = line[2][1]
                quantity['zvals'][y_index,x_index] = line[3+qi][1]

        else:
            raise NotImplementedError('qcodes_with_qtplot only supports plotting 1D and 2D data')
        
        # update plot only every several (self.plotting_interval)
        # seconds to minimize the overhead
        if time.time()-self.last_update_time > self.plotting_interval:
            for qi, quantity in enumerate(self.quantities):
                quantity['plot'].update_plot()
            self.last_update_time = time.time()

        self.point_counter += 1

    def create_plots(self):
        # open each measured quantity in a separate window
        # this allows the user to keep only the "interesting"
        # dataset opened
        for i, quantity in enumerate(self.quantities):
            quantity['plot'] = QtPlot(window_title=quantity['name'],
                        figsize=(450, 300),
                        fig_x_position=int(i/3)*0.25,
                        fig_y_position=(i%3)*0.315)

            if len(self.coordinates) == 1:
                coordinate = self.coordinates[0]

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

            elif len(self.coordinates) == 2:
                coordinateX = self.coordinates[0]
                coordinateY = self.coordinates[1]

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
