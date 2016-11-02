import pysweep.datahandling
import time

# define sweep_object
def sweep_object(parameter, points):
    def fun(x, p):
        parameter.set(x)
        return {}
    return {'set_function': fun,
            'unit': parameter.units,
            'label': parameter.label,
            'point_function': lambda parameter:points}

def sweep(measurement_init, measure, measurement_end, sweep1, sweep2, sweep3):
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
            print(time.asctime(time.localtime(eta)))

    dict_waterfall = measurement_init()

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
    dat = pysweep.datahandling.datafile(cols)
    # do measurement
    for s3 in sweep3['point_function'](dict_waterfall):
        r = sweep3['set_function'](s3, dict_waterfall)
        dict_waterfall.update(r)
        for s2 in sweep2['point_function'](dict_waterfall):
            r = sweep2['set_function'](s2, dict_waterfall)
            dict_waterfall.update(r)
            for s1 in sweep1['point_function'](dict_waterfall):
                r = sweep1['set_function'](s1, dict_waterfall)
                dict_waterfall.update(r)

                dat.write_line([s1, s2, s3] + measure(dict_waterfall))
                t.update(1)
            dat.write_block()
    measurement_end()
    # TODO save station snapshot
    dat.close()
    return dat.filename
