import qcodes as qc
import numpy as np
import time
import h5py
import itertools

fmt = 'D:/data/{date}/{date}_{counter}'

class datafile():
    def __init__(self, columns, dat_format=True, hdf5_format=False, qc_measurement=None):
        self.dat_format = dat_format
        self.hdf5_format = hdf5_format
        io = qc.DiskIO('.')
        loc_provider = qc.data.location.FormatLocation(
            fmt=fmt)
        self.filename = loc_provider(io)
        with io.open(self.filename+'.dat', 'w') as f:
            pass
        self.file = open(self.filename+'.dat', 'w')
        self.metafile = open(self.filename + '.meta.txt', 'w')
        self.columns = columns
        self.write_header()
        self.metafile.close()

        # qc_database part
        self.qc_datasaver = None  # to be set later by the sweeping function
        self.all_colnames = []
        if qc_measurement is not None:
            set_colnames = []
            def extract_lc(name):
                label, unit = name.split(' (')
                return label, unit[:-1]
            for col in columns:
                if col['type'] == 'coordinate':
                    label, unit = extract_lc(col['name'])
                    set_colnames.append(label)
            for col in columns:
                label, unit = extract_lc(col['name'])
                self.all_colnames.append(label)
                if col['type'] == 'coordinate':
                    qc_measurement.register_custom_parameter(label, unit=unit)
                else:
                    qc_measurement.register_custom_parameter(label, unit=unit,
                                                             setpoints=set_colnames)

        # hdf5 part
        dt_list = []
        shape_list = []
        for col in columns:
            if col['type'] == 'coordinate':
                shape_list.append(col['size'])
            dt_list.append(((col['name'], np.float64)))
        shape = tuple(reversed(shape_list))

        if self.hdf5_format:
            self.dtype = np.dtype(dt_list)
            self.data = np.zeros(shape=shape, dtype=self.dtype)
            self.h5_iterator = itertools.product(range(shape[0]), range(shape[1]), range(shape[2]))

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

    def write_line(self, values):
        if self.dat_format:
            self.file.write('\t'.join([str(v) for v in values]) + '\r\n')
            self.file.flush()
        if self.hdf5_format:
            self.data[self.h5_iterator.__next__()] = tuple(values)
        if self.qc_datasaver is not None:
            self.qc_datasaver.add_result(*[(label, value) for label, value in zip(self.all_colnames, values)])


    def write_block(self):
        self.file.write('\r\n')
        self.file.flush()

    def close(self):
        self.file.close()
        if self.hdf5_format:
            h5_file = h5py.File(self.filename + '.h5', 'w')
            h5_file['data'] = self.data
            h5_file.close()

    def __del__(self):
        self.close()
