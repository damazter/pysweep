from pysweep.core.sweepobject import SweepObject
from pysweep.core.measurementfunctions import MakeMeasurementFunction, MeasurementFunction

import time
import numpy as np

def add_function(sweep_object, fun):
    @MakeMeasurementFunction(sweep_object.set_function.paramstruct+fun.paramstruct)
    def wrapper(x, dict_waterfall):
        r = sweep_object.set_function(x, dict_waterfall)
        r2 = fun(dict_waterfall)
        return r+r2
    return SweepObject(wrapper, sweep_object.unit, sweep_object.label, sweep_object.point_function)


def sweep_repetitions(waiting_time, npoints):
    @MakeMeasurementFunction([])
    def fun(x, dict_waterfall):
        time.sleep(waiting_time)
        return []

    @MakeMeasurementFunction([])
    def point_fun(dict_waterfall):
        return range(npoints), []
    return SweepObject(fun, '', 'iteration', point_fun)


def sleep_after_first(sweep_object, sleep_time):
    # create new point and setfunction, to keep track of the number of points already swept over
    # index is an array rather than an int, such that we can reference the same object all the time
    # whereas ints would be immutable, needing a 'global' statement, mixing together namespaces that we want to separate
    index = []
    @MakeMeasurementFunction([])
    def pointfun(dict_waterfall):
        while len(index)>=1:
            index.pop()
        return sweep_object.point_function(dict_waterfall)
    def setfun(x, dict_waterfall):
        r = sweep_object.set_function(x, dict_waterfall)
        if len(index) == 0:
            time.sleep(sleep_time)
            index.append(1)
        return r
    # convert these functions into proper MeasurementFunctions
    pf = MeasurementFunction(pointfun, sweep_object.point_function.paramstruct)
    sf = MeasurementFunction(setfun, sweep_object.set_function.paramstruct)
    # construct a new pointfunction to return
    return SweepObject(sf, sweep_object.unit, sweep_object.label, pointfun, dataparameter=sweep_object.dataparameter)
