# pylint: disable=missing-function-docstring,missing-module-docstring

import json
import os
import sys

from subprocess import check_output, CalledProcessError
from tempfile import NamedTemporaryFile

import pytest

project_folder = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sample_folder = os.path.join(project_folder, 'tinytag', 'tests', 'samples')
mp3_with_image = os.path.join(sample_folder, 'id3image_without_description.mp3')
bogus_file = os.path.join(sample_folder, 'there_is_no_such_ext.bogus')
assert os.path.exists(mp3_with_image)

tinytag_attributes = {'album', 'albumartist', 'artist', 'bitdepth', 'bitrate',
                      'channels', 'comment', 'disc', 'disc_total', 'duration', 'extra',
                      'filesize', 'filename', 'genre', 'samplerate', 'title', 'track',
                      'track_total', 'year'}


def run_cli(args: str) -> str:
    debug_env = str(os.environ.pop("DEBUG", None))
    output = check_output(f'{sys.executable} -m tinytag ' + args, cwd=project_folder, shell=True)
    if debug_env:
        os.environ["DEBUG"] = debug_env
    return output.decode('utf-8')


def file_size(filename: str) -> int:
    return os.stat(filename).st_size


def test_wrong_params() -> None:
    with pytest.raises(CalledProcessError):
        assert 'tinytag [options] <filename' in run_cli('-lol')


def test_print_help() -> None:
    assert 'tinytag [options] <filename' in run_cli('-h')
    assert 'tinytag [options] <filename' in run_cli('--help')


def test_save_image_long_opt() -> None:
    with NamedTemporaryFile() as temp_file:
        assert file_size(temp_file.name) == 0
    run_cli(f'--save-image {temp_file.name} {mp3_with_image}')
    assert file_size(temp_file.name) > 0
    with open(temp_file.name, 'rb') as file_handle:
        image_data = file_handle.read(20)
        assert image_data.startswith(b'\xff')
        assert b'JFIF' in image_data


def test_save_image_short_opt() -> None:
    with NamedTemporaryFile() as temp_file:
        assert file_size(temp_file.name) == 0
    run_cli(f'-i {temp_file.name} {mp3_with_image}')
    assert file_size(temp_file.name) > 0


def test_save_image_bulk() -> None:
    with NamedTemporaryFile(suffix='.jpg') as temp_file:
        temp_file_no_ext = temp_file.name[:-4]
        assert file_size(temp_file.name) == 0
    run_cli(f'-i {temp_file.name} {mp3_with_image} {mp3_with_image} {mp3_with_image}')
    assert not os.path.isfile(temp_file.name)
    assert file_size(temp_file_no_ext + '00000.jpg') > 0
    assert file_size(temp_file_no_ext + '00001.jpg') > 0
    assert file_size(temp_file_no_ext + '00002.jpg') > 0


def test_meta_data_output_default_json() -> None:
    output = run_cli(mp3_with_image)
    data = json.loads(output)
    assert data
    assert set(data.keys()) == tinytag_attributes


def test_meta_data_output_format_json() -> None:
    output = run_cli('-f json ' + mp3_with_image)
    data = json.loads(output)
    assert data
    assert set(data.keys()) == tinytag_attributes


def test_meta_data_output_format_csv() -> None:
    output = run_cli('-f csv ' + mp3_with_image)
    lines = [line for line in output.split(os.linesep) if line]
    assert all(',' in line for line in lines)
    attributes = set(line.split(',')[0] for line in lines)
    assert set(attributes) == tinytag_attributes


def test_meta_data_output_format_tsv() -> None:
    output = run_cli('-f tsv ' + mp3_with_image)
    lines = [line for line in output.split(os.linesep) if line]
    assert all('\t' in line for line in lines)
    attributes = set(line.split('\t')[0] for line in lines)
    assert set(attributes) == tinytag_attributes


def test_meta_data_output_format_tabularcsv() -> None:
    output = run_cli('-f tabularcsv ' + mp3_with_image)
    header, _line, _rest = output.split(os.linesep)
    assert set(header.split(',')) == tinytag_attributes


def test_fail_on_unsupported_file() -> None:
    with pytest.raises(CalledProcessError):
        run_cli(bogus_file)


def test_fail_skip_unsupported_file_long_opt() -> None:
    run_cli('--skip-unsupported ' + bogus_file)


def test_fail_skip_unsupported_file_short_opt() -> None:
    run_cli('-s ' + bogus_file)
