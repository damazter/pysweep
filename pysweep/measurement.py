def none():
    def fun(v, parameters):
        return []
    def pointfunction(parameters):
        return [1]
    return {'set_function': fun,
            'point_function': pointfunction,
            'label': 'None',
            'unit': 'e'}

class Measurement:
    def __init__(self, measurement_init, measurement_end, measure,
          sweep1=none(),
          sweep2=none(),
          sweep3=none()):
        self.measurement_init = measurement_init
        self.measurement_end = measurement_end
        self.sweep1 = sweep1
        self.sweep2 = sweep2
        self.sweep3 = sweep3