import pysweep.databackends.base as base

STUPIDAXES = ['None1', 'None2', 'None3']

class DataBackend(base.DataBackend, base.DataSaver):
    def __init__(self, meas):
        self.meas = meas  # The qcodes measurement object
        self.runner = None
        self.datasaver = None
        self.columns = None

    def setup(self, paramstructure):
        setpoints = []
        self.columns = []
        for param in paramstructure:
            self.columns.append(param.name)
            # Hack to exclude trivial measurement axes
            if param.independent:
                if isinstance(param, base.DataParameterFixedSweep) and param.npoints==1:
                    print(param.name, ', postponing registration')
                else:
                    if not param.duplicate:
                        self.meas.register_custom_parameter(param.name, unit=param.unit, paramtype=param.paramtype)
                    if not param.independent == 2:  # For parameters that will be the independent for a few explicitely defined parameters, we do not want to add it as an automatic independent
                        setpoints.append(param.name)
            else:
                if not param.duplicate:
                    self.meas.register_custom_parameter(param.name, unit=param.unit, paramtype=param.paramtype,
                                                        setpoints=setpoints+param.extra_dependencies)
        # for param in paramstructure:
        #     # Hack to exclude trivial measurement axes
        #     if param.independent:
        #         if isinstance(param, base.DataParameterFixedSweep) and param.npoints==1:
        #             self.meas.register_custom_parameter(param.name, unit=param.unit, paramtype=param.paramtype, setpoints=setpoints)

    def __enter__(self):
        self.runner = self.meas.run()
        self.datasaver = self.runner.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.runner.__exit__(exc_type, exc_val, exc_tb)

    def add_to_line(self, line):
        newline = []
        for entry in line:
            if entry[0] not in STUPIDAXES:
                newline.append(entry)
        self.datasaver.add_result(*newline)

    def write_line(self):
        pass

    def write_block(self):
        pass

# this databackend exists to circumentvent the fact that qcodes only allows a single shape per add_result
class CutDataBackend(DataBackend):
    def __init__(self, meas):
        super().__init__(meas)
        self.all_deps = {}

    def setup(self, paramstructure):
        super().setup(paramstructure)
        # here I can extract some information regarding independents and such...

        setpoints = []
        print([p.independent for p in paramstructure])
        for param in paramstructure:
            if param.name in STUPIDAXES:
                continue
            if param.independent:
                if not param.independent == 2:
                    setpoints.append(param.name)
            else:
                self.all_deps[param.name] = setpoints+param.extra_dependencies

    def add_to_line(self, line):
        # the hard thing is to determine which parameters i should keep, which to remove and when to write
        data = {}
        # implement a stupid check to see that all parameters are written in the end
        param_check = [False]*len(line)
        print(self.all_deps)
        for i, entry in enumerate(line):
            if entry[0] in STUPIDAXES:
                continue
            # keep running tally of all columns, allows fancy overwriting if necessary
            data[entry[0]] = (i, entry[1])
            # if it is a pure dependent, write it, together with all its independents
            if entry[0] in self.all_deps:
                # when I write a line, keep a check which columns I use for that
                newline = []
                for indep in self.all_deps[entry[0]]:
                    newline.append((indep, data[indep][1]))
                    param_check[data[indep][0]] = True
                newline.append((entry[0], entry[1]))
                param_check[i] = True
                self.datasaver.add_result(*newline)

        # check that all values in the line are written somewhere
        for i, written in enumerate(param_check):
            if not written and line[i][0] not in STUPIDAXES:
                raise RuntimeError('I dont know what went wrong, but datacolumn was not written. I rather crash than lose data. Datacolumn: '+ line[i][0]+'_'+str(i))


