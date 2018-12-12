import os
import json
import sys
from tinytag import TinyTag, TinyTagException

def usage():
    print('usage: tinytag <filename> [--save-image <image-path>] [--format json|csv|tsv]')
    sys.exit(1)

def pop_param(name, _default):
    if name in sys.argv:
        idx = sys.argv.index(name)
        sys.argv.pop(idx)
        return sys.argv.pop(idx)
    return _default

try:
    save_image_path = pop_param('--save-image', None)
    formatting = pop_param('--format', 'json')
    filename = sys.argv[1]
except:
    usage()

try:
    tag = TinyTag.get(filename, image=save_image_path is not None)
    if save_image_path:
        image = tag.get_image()
        if image:
            with open(save_image_path, 'wb') as fh:
                fh.write(image)
    if formatting == 'json':
        print(json.dumps(tag.as_dict()))
    elif formatting == 'csv':
        print('\n'.join('%s,%s' % (k, v) for k, v in tag.as_dict().items()))
    elif formatting == 'tsv':
        print('\n'.join('%s\t%s' % (k, v) for k, v in tag.as_dict().items()))
except TinyTagException as e:
    sys.stderr.write(str(e))