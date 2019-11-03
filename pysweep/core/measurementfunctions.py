from pysweep.databackends.base import DataParameter

'''
paramstructure / paramstruct is a list of the DataParameters
'''

class MeasurementFunction:
    def __init__(self, function, paramstruct):
        self.function = function
        self.paramstruct = paramstruct

    def __call__(self, *args, **kwargs) -> list:
        return self.function(*args, **kwargs)


    # The paramstruct method should return a list of DataParameters for each element this
    # Measurement function will return in its __call__ method
    def get_paramstruct(self) -> list:
        return self.paramstruct

# The decorator for the measurement function that takes as an argument
# a dictionary containing arbitrary information, among which there is always
# a Qcodes measurement station under the key 'STATION'
# in most use cases the dictionary is unused in the function definition.
# The function to be decorated must return a list (list type!) with objects
# to be stored.
# In particular in case the measurement function returns both coordinates and
# the measured values these will both be objects in this list
# e.g. [ np.array(frequencies), np.array(S21) ]
# Always return the independent parameters before the dependent parameters in the list.
# paramstruct is a list of the DataParameters of lists containing
# the initialization parameters od DataParameter
# The order in this list corresponds to the order of parameters returned
# by the measurement function.
def MakeMeasurementFunction(paramstruct):
    new_param_struct = []
    for param in paramstruct:
        if isinstance(param, DataParameter):
            new_param_struct.append(param)
        else:
            new_param_struct.append(DataParameter(*param))

    def decorator(function):
        return MeasurementFunction(function, new_param_struct)
    return decorator
