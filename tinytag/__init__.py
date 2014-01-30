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

    def has_all_tags(self):
        return all((self.track, self.track_total, self.title,
                    self.artist, self.album, self.year))

    @classmethod
    def get(cls, filename, tags=True, length=True):
        if filename.lower().endswith('.mp3'):
            return ID3V2(filename, tags=tags, length=length)
        if filename.lower().endswith(('.oga', '.ogg')):
            return Ogg(filename, tags=tags, length=length)

    def __str__(self):
        return str(self.__dict__)

    def load(self, filename, tags, length):
        with open(filename, 'rb') as af:
            if tags:
                self._parse_tag(af)
                af.seek(0)
            if length:
                self._determine_length(af)

    def _set_field(self, fieldname, bytestring, transfunc=None):
        if getattr(self, fieldname):
            return
        if transfunc:
            setattr(self, fieldname, transfunc(bytestring))
        else:
            setattr(self, fieldname, bytestring)

    def _determine_length(self, fh):
        raise NotImplementedError()

    def _parse_tag(self, fh):
        raise NotImplementedError()


class ID3V2(TinyTag):
    FID_TO_FIELD = {  # Mapping from Frame ID to a field of the TinyTag
        'TRCK': 'track',  'TRK': 'track',
        'TYER': 'year',   'TYE': 'year',
        'TALB': 'album',  'TAL': 'album',
        'TPE1': 'artist', 'TP1': 'artist',
        'TIT2': 'title',  'TT2': 'title',
    }

    def __init__(self, filename, tags=True, length=True):
        TinyTag.__init__(self)
        self.load(filename, tags=tags, length=length)

    def _determine_length(self, fh):
        # set sample rate from first found frame later, default to 44khz
        file_sample_rate = 44100
        # see this page for the magic values used in mp3:
        # http://www.mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm
        bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192,
                    224, 256, 320]
        samplerates = [44100, 48000, 32000]
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
                    br_id = (bitrate_freq & 0xf0) >> 4  # biterate id
                    sr_id = (bitrate_freq & 0x03) >> 2  # sample rate id
                    # check if the values aren't just random
                    if br_id == 15 or br_id == 0 or sr_id == 3:
                        #invalid frame! roll back to last position
                        fh.seek(-2, os.SEEK_CUR)
                        continue
                    frames += 1  # it's most probably an mp3 frame
                    bitrate = bitrates[br_id]
                    samplerate = samplerates[sr_id]
                    if frames == 1:
                        file_sample_rate = samplerate
                    padding = 1 if bitrate_freq & 0x02 > 0 else 0
                    frame_length = (144000 * bitrate) // samplerate + padding
                    if frame_length > 1:
                        # jump over current frame body
                        fh.seek(frame_length - header_bytes, os.SEEK_CUR)
        samples = frames * 1152  # 1152 is the default frame size for mp3
        self.length = samples/float(file_sample_rate)

    def _parse_tag(self, fh):
        header = struct.unpack('3sBBB4B', fh.read(10))
        tag = codecs.decode(header[0], 'ISO-8859-1')
        # check if there is an ID3v2 tag at the beginning of the file
        if tag == 'ID3':
            major, rev = header[1:3]
            unsync = header[3] & 0x80 > 0
            extended = header[3] & 0x40 > 0
            experimental = header[3] & 0x20 > 0
            size = self._calc_size_7bit_bytes(header[4:9])
            parsed_size = 0
            while parsed_size < size:
                frame_size = self._parse_frame(fh, is_v22=major == 2)
                if frame_size == 0:
                    break
                parsed_size += frame_size
        if not self.has_all_tags():  # try to get more info using id3v1
            fh.seek(-128, 2)
            if fh.read(3) == b'TAG':  # check if this is an ID3 v1 tag
                asciidecode = lambda x: self._unpad(codecs.decode(x, 'ASCII'))
                self._set_field('title', fh.read(30), transfunc=asciidecode)
                self._set_field('artist', fh.read(30), transfunc=asciidecode)
                self._set_field('album', fh.read(30), transfunc=asciidecode)
                self._set_field('year', fh.read(4), transfunc=asciidecode)
                comment = fh.read(30)
                if b'\x00\x00' < comment[-2:] < b'\x01\x00':
                    self._set_field('track', str(ord(comment[-1:])))

    def _parse_frame(self, fh, is_v22=False):
        encoding = 'ISO-8859-1'
        frame_header_size = 6 if is_v22 else 10
        frame_size_bytes = 3 if is_v22 else 4
        binformat = '3s3B' if is_v22 else '4s4B2B'
        frame = struct.unpack(binformat, fh.read(frame_header_size))
        frame_id = self._decode_string(frame[0])
        frame_size = self._calc_size_7bit_bytes(frame[1:1+frame_size_bytes])
        if frame_size > 0:
            # flags = frame[1+frame_size_bytes:] # dont care about flags.
            content = fh.read(frame_size)
            fieldname = ID3V2.FID_TO_FIELD.get(frame_id)
            if fieldname:
                if fieldname == 'track':
                    self._parse_track(content)
                else:
                    self._set_field(fieldname, content, self._decode_string)
            return frame_size
        return 0

    def _decode_string(self, b):
        # it's not my fault, this is the spec.
        if b[0] == b'\x00' or b[0] == 0:
            return self._unpad(codecs.decode(b[1:], 'ISO-8859-1'))
        if b[0:3] == b'\x01\xff\xfe':
            return self._unpad(codecs.decode(b[3:], 'UTF-16'))
        return self._unpad(codecs.decode(b, 'ISO-8859-1'))

    def _unpad(self, s):
        return s[:s.index('\x00')] if '\x00' in s else s

    def _parse_track(self, b):
        track = self._decode_string(b)
        track_total = None
        if '/' in track:
            track, track_total = track.split('/')
        self._set_field('track', track)
        self._set_field('track_total', track_total)

    def _calc_size_7bit_bytes(self, b):
        if len(b) == 3:  # pad in first byte for id3 v2.2
            b = (0, b[0], b[1], b[2])
        return ((b[0] & 127) << 21) | ((b[1] & 127) << 14) | \
               ((b[2] & 127) << 7) | (b[3] & 127)


class StringWalker(object):
    def __init__(self, string):
        self.string = string
    
    def get(self, length):
        retstring, self.string = self.string[:length], self.string[length:]
        return retstring

class Ogg(TinyTag):
    def __init__(self, filename, tags=True, length=True):
        TinyTag.__init__(self)
        self._tags_parsed = False
        self._max_samplenum = 0  # maximum sample position ever read
        self.load(filename, tags=tags, length=length)

    def _determine_length(self, fh):
        if not self._tags_parsed:
            self._parse_tag(fh)  # parse_whole file to determine length :(

    def _parse_tag(self, fh):
        mapping = {'album': 'album', 'title': 'title',
                   'date': 'year', 'tracknumber': 'track'}
        sample_rate = 44100  # default samplerate 44khz, but update later
        for packet in self._parse_pages(fh):
            walker = StringWalker(packet)
            head = walker.get(7)
            if head == b"\x01vorbis":
                (channels, sample_rate, max_bitrate, nominal_bitrate,
                 min_bitrate) = struct.unpack("<B4i", packet[11:28])
            elif head == b"\x03vorbis":
                vendor_length = struct.unpack('I', walker.get(4))[0]
                vendor = walker.get(vendor_length)
                elements = struct.unpack('I', walker.get(4))[0]
                for i in range(elements):
                    length = struct.unpack('I', walker.get(4))[0]
                    keyvalpair = codecs.decode(walker.get(length), 'UTF-8')
                    if '=' in keyvalpair:
                        key, value = keyvalpair.split('=')
                        fieldname = mapping.get(key.lower())
                        if fieldname:
                            self._set_field(fieldname, value)
        self.length = self._max_samplenum / float(sample_rate)

    def _parse_pages(self, fh):
        previous_page = b''  # contains data from previous (continuing) pages
        header_data = fh.read(27)
        while len(header_data) != 0:
            header = struct.unpack('<4sBBqIIiB', header_data)
            oggs, version, flags, pos, serial, pageseq, crc, segments = header
            self._max_samplenum = max(self._max_samplenum, pos)
            if oggs != b'OggS' or version != 0:
                break  # not a valid ogg file
            segsizes = struct.unpack('B'*segments, fh.read(segments))
            total = 0
            for segsize in segsizes:  # read all segments
                total += segsize
                if total < 255:  # less than 255 bytes means end of page
                    yield previous_page + fh.read(total)
                    previous_page = b''
                    total = 0
            if total != 0:
                if total % 255 == 0:
                    previous_page += fh.read(total)
                else:
                    yield previous_page + fh.read(total)
                    previous_page = b''
            header_data = fh.read(27)
