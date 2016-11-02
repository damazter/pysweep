import qcodes as qc
import time

class datafile():
    def __init__(self, columns):
        io = qc.DiskIO('.')
        loc_provider = qc.data.location.FormatLocation(
            fmt='C:/data/{date}/{date}_{counter}')
        self.filename = loc_provider(io)
        with io.open(self.filename+'.dat', 'w') as f:
            pass
        self.file = open(self.filename+'.dat', 'w')
        self.metafile = open(self.filename + '.meta.txt', 'w')
        self.columns = columns
        self.write_header()
        self.metafile.close()


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
            self.metafile.write(str(col['start'])+'\r\n')
            self.metafile.write(str(col['end']) + '\r\n')
            self.metafile.write(str(col['name']) + '\r\n')
        else:
            self.metafile.write(str(nr+1)+'\r\n')
            self.metafile.write(col['name'] + '\r\n')

    def write_line(self, values):
        self.file.write('\t'.join([str(v) for v in values]) + '\r\n')
        self.file.flush()

    def write_block(self):
        self.file.write('\r\n')
        self.file.flush()

    def close(self):
        self.file.close()

    def __del__(self):
        self.close()
