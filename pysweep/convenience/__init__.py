from pysweep.core.sweepobject import SweepObject
from pysweep.core.measurementfunctions import MakeMeasurementFunction

def add_function(sweep_object, fun):
    @MakeMeasurementFunction(sweep_object.set_function.paramstruct+fun.paramstruct)
    def wrapper(x, dict_waterfall):
        r = sweep_object.set_function(x, dict_waterfall)
        r2 = fun(dict_waterfall)
        return r+r2
    return SweepObject(wrapper, sweep_object.unit, sweep_object.label, sweep_object.point_function)