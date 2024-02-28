# pylint: disable=missing-module-docstring,protected-access

from os.path import splitext
import json
import os
import sys

from tinytag.tinytag import TinyTag


def _usage():
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


def _pop_param(name, _default):
    if name in sys.argv:
        idx = sys.argv.index(name)
        sys.argv.pop(idx)
        return sys.argv.pop(idx)
    return _default


def _pop_switch(name, _default):
    if name in sys.argv:
        idx = sys.argv.index(name)
        sys.argv.pop(idx)
        return True
    return False


def _print_tag(tag, formatting, header_printed=False):
    data = {'filename': tag._filename}
    data.update(tag._as_dict())
    if formatting == 'json':
        print(json.dumps(data))
        return header_printed
    for field, value in data.items():
        if isinstance(value, str):
            data[field] = value.replace('\x00', ';')  # use a more friendly separator for output
    if formatting == 'csv':
        print('\n'.join(f'{field},{value}' for field, value in data.items()))
    elif formatting == 'tsv':
        print('\n'.join(f'{field}\t{value}' for field, value in data.items()))
    elif formatting == 'tabularcsv':
        if not header_printed:
            print(','.join(field for field, value in data.items()))
            header_printed = True
        print(','.join(f'"{value}"' for field, value in data.items()))
    return header_printed


def _run():
    display_help = _pop_switch('--help', False) or _pop_switch('-h', False)
    if display_help:
        _usage()
        return 0
    save_image_path = _pop_param('--save-image', None) or _pop_param('-i', None)
    formatting = (_pop_param('--format', None) or _pop_param('-f', None)) or 'json'
    skip_unsupported = _pop_switch('--skip-unsupported', False) or _pop_switch('-s', False)
    filenames = sys.argv[1:]
    header_printed = False

    for i, filename in enumerate(filenames):
        if skip_unsupported and not (TinyTag.is_supported(filename) and os.path.isfile(filename)):
            continue
        try:
            tag = TinyTag.get(filename, image=save_image_path is not None)
            if save_image_path:
                # allow for saving the image of multiple files
                actual_save_image_path = save_image_path
                if len(filenames) > 1:
                    actual_save_image_path, ext = splitext(actual_save_image_path)
                    actual_save_image_path += f'{i:05d}{ext}'
                image = tag.get_image()
                if image:
                    with open(actual_save_image_path, 'wb') as file_handle:
                        file_handle.write(image)
            header_printed = _print_tag(tag, formatting, header_printed)
        except Exception as exc:  # pylint: disable=broad-except
            sys.stderr.write(f'{filename}: {exc}\n')
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(_run())
