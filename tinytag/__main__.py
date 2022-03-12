from __future__ import absolute_import
from os.path import splitext
import os
import json
import sys

from tinytag.tinytag import TinyTag, TinyTagException


def usage():
    print('''tinytag [options] <filename...>

    -h, --help
        Display help

    -i, --save-image <image-path>
        Save the cover art to a file

    -f, --format json|csv|tsv|tabularcsv
        Specify how the output should be formatted

    -s, --skip-unsupported
        Skip files that do not have a file extension supported by tinytag

''')


def pop_param(name, _default):
    if name in sys.argv:
        idx = sys.argv.index(name)
        sys.argv.pop(idx)
        return sys.argv.pop(idx)
    return _default


def pop_switch(name, _default):
    if name in sys.argv:
        idx = sys.argv.index(name)
        sys.argv.pop(idx)
        return True
    return False


try:
    display_help = pop_switch('--help', False) or pop_switch('-h', False)
    if display_help:
        usage()
        sys.exit(0)
    save_image_path = pop_param('--save-image', None) or pop_param('-i', None)
    formatting = (pop_param('--format', None) or pop_param('-f', None)) or 'json'
    skip_unsupported = pop_switch('--skip-unsupported', False) or pop_switch('-s', False)
    filenames = sys.argv[1:]
except Exception as exc:
    print(exc)
    usage()
    sys.exit(1)

header_printed = False

for i, filename in enumerate(filenames):
    try:
        if skip_unsupported:
            if os.path.isdir(filename):
                continue
            if not TinyTag.is_supported(filename):
                continue
        tag = TinyTag.get(filename, image=save_image_path is not None)
        if save_image_path:
            # allow for saving the image of multiple files
            actual_save_image_path = save_image_path
            if len(filenames) > 1:
                actual_save_image_path, ext = splitext(actual_save_image_path)
                actual_save_image_path += '%05d' % i + ext
            image = tag.get_image()
            if image:
                with open(actual_save_image_path, 'wb') as fh:
                    fh.write(image)
        data = {'filename': filename}
        data.update(tag.as_dict())
        if formatting == 'json':
            print(json.dumps(data))
        elif formatting == 'csv':
            print('\n'.join('%s,%s' % (k, v) for k, v in data.items()))
        elif formatting == 'tsv':
            print('\n'.join('%s\t%s' % (k, v) for k, v in data.items()))
        elif formatting == 'tabularcsv':
            if not header_printed:
                print(','.join(k for k, v in data.items()))
                header_printed = True
            print(','.join('"%s"' % v for k, v in data.items()))
    except TinyTagException as e:
        sys.stderr.write('%s: %s\n' % (filename, str(e)))
        sys.exit(1)
