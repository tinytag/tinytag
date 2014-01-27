import codecs
import struct
import os

class TinyTag(object):
    def __init__(self):
        self.track = None
        self.track_total = None
        self.title = None
        self.artist = None
        self.album = None
        self.year = None
        self.length = 0

    @classmethod
    def get(cls, filename, get_tags=True, get_length=True):
        if filename.lower().endswith('.mp3'):
            return ID3V2(filename, get_tags=get_tags, get_length=get_length)
    
class ID3V2(TinyTag):
    FRAME_ID_ASSIGNMENT = {
        'TRCK': '_parse_track',
        'TRK': '_parse_track',
        'TYER': '_parse_year',
        'TYE': '_parse_year',
        'TALB': '_parse_album',
        'TAL': '_parse_album',
        'TPE1': '_parse_artist',
        'TP1': '_parse_artist',
        'TIT2': '_parse_title',
        'TT2': '_parse_title',
    }

    def __init__(self, filename):
        TinyTag.__init__(self)
        self.load(filename)

    def __str__(self):
        return str(self.__dict__)

    def load(self, filename, get_tags=True, get_length=True):
        with open(filename, 'rb') as af:
            if get_tags:
                self._parse_id3v2(af)
                af.seek(0)
            if get_length:
                self._determine_length(af)
            

    def _determine_length(self, fh):
        # set sample rate from first found frame later, default to 44khz
        file_sample_rate = 44100
        # see this page for the magic values used in mp3:
        # http://www.mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm
        bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192,
                    224, 256, 320]
        samplerates = [44100, 48000, 32000]
        samples_per_frame = 1152
        header_bytes = 4
        frames = 0
        while True:
            # reading through garbage until 12 '1' bits are found
            b = fh.read(1)
            if len(b) == 0:
                break
            if b == b'\xff':
                b = fh.read(1)
                if b > b'\xf0':
                    bitrate_freq, rest = struct.unpack('BB', fh.read(2))
                    bitrate_selector = (bitrate_freq & 0xf0) >> 4
                    sample_rate_selector = (bitrate_freq&0x03)>>2
                    # check if the values aren't just random
                    if bitrate_selector == 15 or bitrate_selector == 0 \
                        or sample_rate_selector == 3:
                        #invalid frame! roll back to last position
                        fh.seek(-2, os.SEEK_CUR)
                        continue
                    # it's most probably an mp3 frame
                    frames += 1
                    bitrate = bitrates[bitrate_selector]
                    samplerate = samplerates[sample_rate_selector]
                    if frames == 1:
                        file_sample_rate = samplerate
                    padding = 1 if bitrate_freq & 0x02 > 0 else 0
                    frame_length = (144000 * bitrate) // samplerate + padding
                    if frame_length > 1:
                        # jump over current frame body
                        fh.seek(frame_length - header_bytes, os.SEEK_CUR)
        samples = frames * samples_per_frame
        self.length = samples*1000//file_sample_rate

    def _parse_id3v2(self, fh):
        header = struct.unpack('3sBBB4B', fh.read(10))
        tag = codecs.decode(header[0], 'ISO-8859-1')
        if not tag == 'ID3':
            # there is no ID3v2 tag at the beginning of the file
            return
        major, rev = header[1:3]
        unsync = header[3] & 0x80 > 0
        extended = header[3] & 0x40 > 0
        experimental = header[3] & 0x20 > 0
        size = self._calc_size(header[4:9])
        parsed_size = 0
        while parsed_size < size:
            frame_size = self._parse_frame(fh, is_v22=major==2)
            if frame_size == 0:
                break
            parsed_size += frame_size

    def _parse_frame(self, fh, is_v22=False):
        encoding = 'ISO-8859-1'
        frame_header_size = 6 if is_v22 else 10 
        frame_size_bytes = 3 if is_v22 else 4
        binformat = '3s3B' if is_v22 else '4s4B2B'
        frame = struct.unpack(binformat, fh.read(frame_header_size))
        frame_id = self._decode_string(frame[0])
        frame_size = self._calc_size(frame[1:1+frame_size_bytes])
        if frame_size > 0:
            # flags = frame[1+frame_size_bytes:] # fuck flags.
            content = fh.read(frame_size)
            if frame_id in ID3V2.FRAME_ID_ASSIGNMENT:
                getattr(self, ID3V2.FRAME_ID_ASSIGNMENT[frame_id])(content)
            return frame_size
        return 0
    
    def _decode_string(self, b):
        # it's not my fault, this is the spec.
        if b[0] == b'\x00' or b[0] == 0:
            return self._unpad(codecs.decode(b[1:], 'ISO-8859-1'))
        if b[0:3] == b'\x01\xff\xfe':
            return self._unpad(codecs.decode(b[3:], 'UTF-16'))
        return self._unpad(codecs.decode(b, 'ISO-8859-1'))
    
    def _unpad(self, string):
        return string[:-1] if string.endswith('\x00') else string
    
    def _parse_track(self, b):
        trackstr = self._decode_string(b)
        if '/' in trackstr:
            self.track, self.track_total = trackstr.split('/')
        else:
            self.track = trackstr

    def _parse_year(self, b):
        self.year = self._decode_string(b)
    
    def _parse_album(self, b):
        self.album = self._decode_string(b)

    def _parse_artist(self, b):
        self.artist = self._decode_string(b)

    def _parse_title(self, b):
        self.title = self._decode_string(b)

    def _dont_care(self, b):
        pass
    
    def _calc_size(self, b):
        # size is saved in 4 bytes with the MSBit 0, so there are 28bits
        if len(b) == 3: #id3v22
            b = (0, b[0], b[1], b[2])
        return ((b[0]&127)<<21) | ((b[1]&127)<<14) | ((b[2]&127)<<7) | (b[3]&127)
