import time
from IPython.display import clear_output
from pysweep.databackends.base import DataParameter, DataParameterFixedSweep
from pysweep.core.sweepobject import SweepObject
from pysweep.core.measurementfunctions import MeasurementFunction, MakeMeasurementFunction

STATION = None  # a way to set the station as a module property
databackend = None


# define sweep_object
def sweep_object(parameter, points):
    @MakeMeasurementFunction([])
    def fun(x, p):
        parameter.set(x)
        return []
    return SweepObject(fun, parameter.unit, parameter.label, lambda d:points)

def none(id):
    @MakeMeasurementFunction([])
    def fun(v, parameters):
        return []
    return SweepObject(fun, 'e', 'None'+str(id), lambda p:[1])

def sweep(measurement_init, measurement_end, measure,
          sweep1=none(1),
          sweep2=none(2),
          sweep3=none(3)):
    if not callable(measure):
        slist = [*measure, sweep1, sweep2, sweep3]
        for s in slist[4:]:
            if not s['label'].startswith('None'):
                raise Exception('Two many sweepers')
        measure, sweep1, sweep2, sweep3 = slist[0:4]
    class timer():
        def __init__(self, npoints):
            # save the starting time upon instantiating this class
            self.starttime = time.time()
            self.lastprint = time.time()
            self.npoints = npoints
            self.point = 0

        def update(self, delta):
            # update the amount of points that have been measured
            self.point += delta
            # if more than a minute has passed since the previous update,
            # check for user interrupts and print expected
            # time of completion
            if time.time() - self.lastprint > 60:
                self.lastprint = time.time()
                self.output(self.starttime + self.npoints * (
                time.time() - self.starttime) / self.point)
            return "0"

        def output(self, eta):
            # function for printing from the timer,
            # here code could be added to send this information to
            # anything that is interested
            clear_output()
            print(time.asctime(time.localtime(eta)))

    dict_waterfall = {'STATUS': 'INIT', 'STATION': STATION}
    measurement_init(dict_waterfall)
    if dict_waterfall['STATION'] is None:
        raise ValueError("The 'measurement_init' function does not yield a "
                         "dictionary with a 'STATION' entry inside")


    #TODO create datafile here

    t = timer(len(sweep1.point_function(dict_waterfall)) *
              len(sweep2.point_function(dict_waterfall)) *
              len(sweep3.point_function(dict_waterfall)))
    def so2c(so):
        points=so.point_function(dict_waterfall)
        return DataParameterFixedSweep(so.label, so.unit, 'numeric', points[0], points[-1], len(points))

    cols = [so2c(sweep3)]
    for param in sweep3.set_function.get_paramstruct():
        cols.append(param)

    cols.append(so2c(sweep2))
    for param in sweep2.set_function.get_paramstruct():
        cols.append(param)

    cols.append(so2c(sweep1))
    for param in sweep1.set_function.get_paramstruct():
        cols.append(param)

    for param in measure.get_paramstruct():
        cols.append(param)

    databackend.setup(cols)
    colnames = [col.name for col in cols]

    with databackend as pysweep_datasaver:
        # do measurement
        dict_waterfall.update({'STATUS': 'RUN'})
        for s3 in sweep3.point_function(dict_waterfall):
            s3_measure = sweep3.set_function(s3, dict_waterfall)
            for s2 in sweep2.point_function(dict_waterfall):
                s2_measure = sweep2.set_function(s2, dict_waterfall)
                for s1 in sweep1.point_function(dict_waterfall):
                    s1_measure = sweep1.set_function(s1, dict_waterfall)

                    data = [s3] + s3_measure + [s2] + s2_measure + [s1] + s1_measure + measure(dict_waterfall)
                    pysweep_datasaver.add_to_line(list(zip(colnames, data)))
                    pysweep_datasaver.write_line()
                    t.update(1)
                    pysweep_datasaver.write_block()
        dict_waterfall.update({'STATUS': 'STOP'})
        measurement_end(dict_waterfall)
    
    return pysweep_datasaver

