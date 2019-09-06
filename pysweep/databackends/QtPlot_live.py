import numpy as np
import time

import qcodes as qc
from qcodes.plots.pyqtgraph import QtPlot
from qcodes.instrument.base import Instrument
from qcodes.utils import validators as vals
from qcodes.instrument.parameter import ManualParameter

from pysweep.databackends.base import DataParameter, DataParameterFixedSweep
import pysweep.databackends.base as base

fmt = 'D:/Data/{date}/{date}_{counter}'

class QtPlot_live_plotter(base.DataBackend, base.DataSaver):
    '''
    This is a PycQED-inspired data backend for live plotting of the data.
    
    The idea is to use for plotting an independent data backend,
    that is independent on backend used for data saving.
    This will be handy for a live-view with fast dual-rastering when
    data saving is not needed.

    The backend uses QtPlot from QCoDeS for live plotting. Since plotting
    runs in the same thread as the measurement it introduces an overhead
    that comes from opening of the windows with plots and updating them.
    With plotting_interval=3 (seconds) overhead in measurement
    is relatively small (~10%).

    The backend has an option of outputting a PNG image at the end
    of the measurement. The directory in which they are saved and
    plot titles indicate at this point data storage location
    consistent with the spyview backend.

    At this time only 1D and 2D datasets are supported. 2D datasets
    will show correctly only if they are on a regular grid
    '''

    def __init__(self, plotting_interval: float=3, export_png=True):

        self.plotting_interval = plotting_interval

        self.io = qc.DiskIO('.')
        loc_provider = qc.data.location.FormatLocation(
            fmt=fmt)
        self.directory_prefix = loc_provider(self.io)
        self.filename_prefix = self.directory_prefix.split('/')[-1]

        self.export_png = export_png
        print(self.directory_prefix)

    def setup(self, paramstructure):

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
        # a counter used to select where the new data point
        # should be inserted
        self.point_counter = 0
        # initialize timer for live update
        self.last_update_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # at the end update the plots for the last time
        # and export figures
        for qi, quantity in enumerate(self.quantities):
            quantity['plot'].update_plot()

            if self.export_png:
                filename = '_'.join([self.directory_prefix, quantity['name']+'.png'])
                quantity['plot'].save(filename=filename)

    def create_plots(self):
        # open each measured quantity in a separate window
        # this allows the user to keep only the "interesting"
        # dataset opened
        for i, quantity in enumerate(self.quantities):
            quantity['plot'] = QtPlot(window_title=quantity['name'],
                        figsize=(450, 300),
                        fig_x_position=(i%4)*0.25,
                        fig_y_position=int(i/4)*0.33)

            plot_title = ' '.join([self.filename_prefix, quantity['name']])
            quantity['plot'].subplots[0].setTitle(plot_title)

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
                raise NotImplementedError('QtPlot_live only supports plotting 1D and 2D data')

    def add_to_line(self, columns):
        if len(self.coordinates) == 1:
            for qi, quantity in enumerate(self.quantities):
                quantity['xvals'][self.point_counter] = columns[2][1]
                quantity['yvals'][self.point_counter] = columns[3+qi][1]
        elif len(self.coordinates) == 2:
            for qi, quantity in enumerate(self.quantities):
                x_index = self.point_counter % self.coordinates[0]['size']
                y_index = int((self.point_counter - x_index)/self.coordinates[0]['size'])

                # commented out because I can't get the irregular grid
                # to work [FKM], TODO
                # quantity['xvals'][y_index] = columns[1][1]
                # quantity['yvals'][x_index] = columns[2][1]
                quantity['zvals'][y_index,x_index] = columns[3+qi][1]

        else:
            raise NotImplementedError('QtPlot_live only supports plotting 1D and 2D data')
        
        # update plot only every several (self.plotting_interval)
        # seconds to minimize the overhead
        if time.time()-self.last_update_time > self.plotting_interval:
            for qi, quantity in enumerate(self.quantities):
                quantity['plot'].update_plot()
            self.last_update_time = time.time()

        self.point_counter += 1
        pass

    def write_line(self):
        pass

    def write_block(self):
        pass