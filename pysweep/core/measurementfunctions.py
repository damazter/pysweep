from pysweep.databackends.base import DataParameter

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
