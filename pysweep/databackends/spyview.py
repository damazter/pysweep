import qcodes as qc
import time
import inspect
from pysweep.databackends.base import DataParameter, DataParameterFixedSweep
import pysweep
import json


import pysweep.databackends.base as base

fmt = 'D:/Data/{date}/{date}_{counter}'


class DataBackend(base.DataBackend, base.DataSaver):
    def __init__(self):
        self.io = qc.DiskIO('.')
        loc_provider = qc.data.location.FormatLocation(
            fmt=fmt)
        self.filename = loc_provider(self.io)
        self.runner = None

        self.columns = None
        self.column_lookup = None
        self.line = None


    def setup(self, paramstructure):
        self.columns = []
        self.column_lookup = {}

        index = 0
        for param in paramstructure:
            if param.name in self.column_lookup:
                raise Exception('Multiple columns with name: ', param.name)
            self.column_lookup[param.name] = index
            index += 1
            if param.paramtype != 'numeric':
                raise Exception('spyview databackend only supports numeric parameters')
            name = param.name+' ('+param.unit+')'
            if isinstance(param, DataParameterFixedSweep):
                self.columns.append({'name': name,
                                     'type': 'coordinate',
                                     'start': param.start,
                                     'end': param.stop,
                                     'size': param.npoints})
            else:
                self.columns.append({'name': name,
                                     'type': 'value'})
        self.line = [None]*len(self.columns)

    def write_python(self, code_file):
        # Write function definitions to file
        # code_file.write(inspect.getsource(measurement_init))
        # code_file.write(inspect.getsource(measurement_end))
        # code_file.write(inspect.getsource(measure))
        # if not sweep1['label'] is 'None':
        #     code_file.write("sweep1: {")
        #     code_file.write("\nset_function:\n" + inspect.getsource(sweep1['set_function']))
        #     code_file.write("\npoint_function:\n" + inspect.getsource(sweep1['point_function']))
        #     code_file.write("\nunit: " + sweep1['unit'])
        #     code_file.write("\nlabel: " + sweep1['label'])
        #     code_file.write("}")
        # if not sweep2['label'] is 'None':
        #     code_file.write("sweep2: {")
        #     code_file.write("\nset_function:\n" + inspect.getsource(sweep2['set_function']))
        #     code_file.write("\npoint_function:\n" + inspect.getsource(sweep2['point_function']))
        #     code_file.write("\nunit: " + sweep2['unit'])
        #     code_file.write("\nlabel: " + sweep2['label'])
        #     code_file.write("}")
        # if not sweep3['label'] is 'None':
        #     code_file.write("sweep3: {")
        #     code_file.write("\nset_function:\n" + inspect.getsource(sweep3['set_function']))
        #     code_file.write("\npoint_function:\n" + inspect.getsource(sweep3['point_function']))
        #     code_file.write("\nunit: " + sweep3['unit'])
        #     code_file.write("\nlabel: " + sweep3['label'])
        #     code_file.write("}")
        # code_file.write("\n\n")
        frame = inspect.stack(context=21)[1]
        try:
            for line in frame.code_context:
                code_file.write(str(line))
        finally:
            del frame

    def __enter__(self):
        self.runner = self.io.open(self.filename + '.dat', 'w')
        self.file = self.runner.__enter__()
        self.metafile = open(self.filename + '.meta.txt', 'w')
        self.write_header()
        self.metafile.close()
        # Save snapshot of the station
        with open(str(self.filename) + '.json', 'w') as settings_file:
            json.dump(pysweep.STATION.snapshot(), settings_file, indent=4)
        with open(str(self.filename) + '.py', 'w') as code_file:
            self.write_python(code_file)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.runner.__exit__(exc_type, exc_val, exc_tb)

    def add_to_line(self, columns):
        # update the self.line variable with the set of values that we are currently getting
        for column in columns:
            self.line[self.column_lookup[column[0]]] = column[1]

    def write_line(self):
        self.file.write('\t'.join([str(v) for v in self.line]) + '\r\n')
        self.file.flush()

    def write_block(self):
        self.file.write('\r\n')
        self.file.flush()

    def write_header(self):
        filename = self.filename.split("/")[-1]
        self.file.write('# Filename: '+filename+'.dat\r\n')
        self.file.write('# Timestamp: '+str(time.asctime())+'\r\n')
        self.file.write('\r\n')

        for i, c in enumerate(self.columns):
            self.write_column_header(i, c)

        self.file.write('\r\n')
        self.file.flush()

    def write_column_header(self, nr, col):
        # write file column header
        self.file.write('# Column '+str(nr+1)+':\r\n')
        for key, val in col.items():
            self.file.write('#\t'+str(key)+': '+str(val)+'\r\n')

        # write metafile lines
        if col['type'] is 'coordinate':
            self.metafile.write(str(col['size']) + '\r\n')
            if not nr == 1:  # I hate people
                self.metafile.write(str(col['start']) + '\r\n')
                self.metafile.write(str(col['end']) + '\r\n')
            else:
                self.metafile.write(str(col['end']) + '\r\n')
                self.metafile.write(str(col['start'])+'\r\n')
            self.metafile.write(str(col['name']) + '\r\n')
        else:
            self.metafile.write(str(nr+1)+'\r\n')
            self.metafile.write(col['name'] + '\r\n')




