# SPDX-FileCopyrightText: 2020-2024 tinytag Contributors
# SPDX-License-Identifier: MIT

# pylint: disable=missing-function-docstring,missing-module-docstring

import json
import os
import sys

from subprocess import check_output, CalledProcessError, STDOUT
from tempfile import NamedTemporaryFile

import pytest

project_folder = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sample_folder = os.path.join(project_folder, 'tinytag', 'tests', 'samples')
mp3_with_img = os.path.join(sample_folder, 'image-text-encoding.mp3')
bogus_file = os.path.join(sample_folder, 'there_is_no_such_ext.bogus')
assert os.path.exists(mp3_with_img)

tinytag_attributes = {
    'album', 'albumartist', 'artist', 'bitdepth', 'bitrate',
    'channels', 'comment', 'composer', 'disc', 'disc_total', 'duration',
    'filesize', 'filename', 'genre', 'samplerate', 'title', 'track',
    'track_total', 'year'
}


def run_cli(args: str) -> str:
    debug_env = str(os.environ.pop("TINYTAG_DEBUG", None))
    output = check_output(
        f'{sys.executable} -m tinytag ' + args, cwd=project_folder,
        shell=True, stderr=STDOUT)
    if debug_env:
        os.environ["TINYTAG_DEBUG"] = debug_env
    return output.decode('utf-8')


def file_size(filename: str) -> int:
    return os.stat(filename).st_size


def test_wrong_params() -> None:
    with pytest.raises(CalledProcessError) as excinfo:
        run_cli('-lol')
    output = excinfo.value.stdout.strip()
    assert output == b"-lol: [Errno 2] No such file or directory: '-lol'"


def test_print_help() -> None:
    assert 'tinytag [options] <filename' in run_cli('-h')
    assert 'tinytag [options] <filename' in run_cli('--help')


def test_save_image_long_opt() -> None:
    with NamedTemporaryFile() as temp_file:
        assert file_size(temp_file.name) == 0
    run_cli(f'--save-image {temp_file.name} {mp3_with_img}')
    assert file_size(temp_file.name) > 0
    with open(temp_file.name, 'rb') as file_handle:
        image_data = file_handle.read(20)
        assert image_data.startswith(b'\xff')
        assert b'JFIF' in image_data


def test_save_image_short_opt() -> None:
    with NamedTemporaryFile() as temp_file:
        assert file_size(temp_file.name) == 0
    run_cli(f'-i {temp_file.name} {mp3_with_img}')
    assert file_size(temp_file.name) > 0


def test_save_image_bulk() -> None:
    temp_name = None
    with NamedTemporaryFile(suffix='.jpg') as temp_file:
        temp_name = temp_file.name
        temp_name_no_ext = temp_name[:-4]
        assert file_size(temp_name) == 0
    run_cli(f'-i {temp_name} {mp3_with_img} {mp3_with_img} {mp3_with_img}')
    assert not os.path.isfile(temp_name)
    assert file_size(temp_name_no_ext + '00000.jpg') > 0
    assert file_size(temp_name_no_ext + '00001.jpg') > 0
    assert file_size(temp_name_no_ext + '00002.jpg') > 0


def test_meta_data_output_default_json() -> None:
    output = run_cli(mp3_with_img)
    data = json.loads(output)
    assert data
    assert set(data.keys()).issubset(tinytag_attributes)


def test_meta_data_output_format_json() -> None:
    output = run_cli('-f json ' + mp3_with_img)
    data = json.loads(output)
    assert data
    assert set(data.keys()).issubset(tinytag_attributes)


def test_meta_data_output_format_csv() -> None:
    output = run_cli('-f csv ' + mp3_with_img)
    lines = [line for line in output.split(os.linesep) if line]
    assert all(',' in line for line in lines)
    attributes = set(line.split(',')[0] for line in lines)
    assert set(attributes).issubset(tinytag_attributes)


def test_meta_data_output_format_tsv() -> None:
    output = run_cli('-f tsv ' + mp3_with_img)
    lines = [line for line in output.split(os.linesep) if line]
    assert all('\t' in line for line in lines)
    attributes = set(line.split('\t')[0] for line in lines)
    assert set(attributes).issubset(tinytag_attributes)


def test_meta_data_output_format_tabularcsv() -> None:
    output = run_cli('-f tabularcsv ' + mp3_with_img)
    header, _line, _rest = output.split(os.linesep)
    assert set(header.split(',')).issubset(tinytag_attributes)


def test_meta_data_output_format_invalid() -> None:
    output = run_cli('-f invalid ' + mp3_with_img)
    assert not output


def test_fail_on_unsupported_file() -> None:
    with pytest.raises(CalledProcessError):
        run_cli(bogus_file)


def test_fail_skip_unsupported_file_long_opt() -> None:
    run_cli('--skip-unsupported ' + bogus_file)


def test_fail_skip_unsupported_file_short_opt() -> None:
    run_cli('-s ' + bogus_file)
