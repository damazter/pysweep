import pysweep.datahandling
import time
import json
import inspect
from IPython.display import clear_output

STATION = None  # a way to set the station as a module property


# define sweep_object
def sweep_object(parameter, points):
    def fun(x, p):
        parameter.set(x)
        return []
    return {'set_function': fun,
            'unit': parameter.units,
            'label': parameter.label,
            'point_function': lambda parameter:points,
            'parameter': parameter}

def none():
    def fun(v, parameters):
        return []
    return {'set_function': fun,
            'point_function': lambda p:[1],
            'label': 'None',
            'unit': 'e'}

def sweep(measurement_init, measurement_end, measure,
          sweep1=none(),
          sweep2=none(),
          sweep3=none()):
    if not callable(measure):
        slist = [*measure, sweep1, sweep2, sweep3]
        for s in slist[4:]:
            if not s['label'] is 'None':
                raise Exception('Two many sweepers')
        measure, sweep1, sweep2, sweep3 = slist[0:4]
    if sweep1['set_function'].__doc__ is None:
        sweep1['set_function'].__doc__ = ''
    if sweep2['set_function'].__doc__ is None:
        sweep2['set_function'].__doc__ = ''
    if sweep3['set_function'].__doc__ is None:
        sweep3['set_function'].__doc__ = ''
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

    t = timer(len(sweep1['point_function'](dict_waterfall)) *
              len(sweep2['point_function'](dict_waterfall)) *
              len(sweep3['point_function'](dict_waterfall)))
    def so2c(so):
        points=so['point_function'](dict_waterfall)
        return {'end': points[-1],
                'name': so['label']+' ('+so['unit']+')',
                'size': len(points),
                'start': points[0],
                'type': 'coordinate'}
    cols = [so2c(sweep1), so2c(sweep2), so2c(sweep3)]

    for col in measure.__doc__.replace("  ","").split("\n"):
        if col is not "":
            cols.append({'name': col, 'type': 'value'})
    for col in sweep1['set_function'].__doc__.replace("  ","").split("\n"):
        if col is not "":
            cols.append({'name': col, 'type': 'value'})
    for col in sweep2['set_function'].__doc__.replace("  ","").split("\n"):
        if col is not "":
            cols.append({'name': col, 'type': 'value'})
    for col in sweep3['set_function'].__doc__.replace("  ","").split("\n"):
        if col is not "":
            cols.append({'name': col, 'type': 'value'})

    dat = pysweep.datahandling.datafile(cols)

    dict_waterfall.update({'FILENAME': dat.filename})
    # Save snapshot of the station
    with open(str(dat.filename) + '.json', 'w') as settings_file:
        json.dump(dict_waterfall['STATION'].snapshot(), settings_file, indent=4)

    # Write function definitions to file
    with open(str(dat.filename) + '.py', 'w') as code_file:
        code_file.write(inspect.getsource(measurement_init))
        code_file.write(inspect.getsource(measurement_end))
        code_file.write(inspect.getsource(measure))
        if not sweep1['label'] is 'None':
            code_file.write("sweep1: {")
            code_file.write("\nset_function:\n"+inspect.getsource(sweep1['set_function']))
            code_file.write("\npoint_function:\n"+inspect.getsource(sweep1['point_function']))
            code_file.write("\nunit: "+sweep1['unit'])
            code_file.write("\nlabel: "+sweep1['label'])
            code_file.write("}")
        if not sweep2['label'] is 'None':
            code_file.write("sweep2: {")
            code_file.write("\nset_function:\n"+inspect.getsource(sweep2['set_function']))
            code_file.write("\npoint_function:\n"+inspect.getsource(sweep2['point_function']))
            code_file.write("\nunit: "+sweep2['unit'])
            code_file.write("\nlabel: "+sweep2['label'])
            code_file.write("}")
        if not sweep3['label'] is 'None':
            code_file.write("sweep3: {")
            code_file.write("\nset_function:\n"+inspect.getsource(sweep3['set_function']))
            code_file.write("\npoint_function:\n"+inspect.getsource(sweep3['point_function']))
            code_file.write("\nunit: "+sweep3['unit'])
            code_file.write("\nlabel: "+sweep3['label'])
            code_file.write("}")
        code_file.write("\n\n")
        frame = inspect.stack(context=21)[1]
        try:
            for line in frame.code_context:
                code_file.write(str(line))
        finally:
            del frame



    # do measurement
    dict_waterfall.update({'STATUS': 'RUN'})
    for s3 in sweep3['point_function'](dict_waterfall):
        s3_measure = sweep3['set_function'](s3, dict_waterfall)
        for s2 in sweep2['point_function'](dict_waterfall):
            s2_measure = sweep2['set_function'](s2, dict_waterfall)
            for s1 in sweep1['point_function'](dict_waterfall):
                s1_measure = sweep1['set_function'](s1, dict_waterfall)
                dat.write_line([s1, s2, s3] + measure(dict_waterfall)+ s1_measure + s2_measure + s3_measure)
                t.update(1)
            dat.write_block()
    dict_waterfall.update({'STATUS': 'STOP'})
    measurement_end(dict_waterfall)
    # TODO save station snapshot
    dat.close()
    return dat.filename
