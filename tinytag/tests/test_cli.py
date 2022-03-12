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

tinytag_attributes = {'album', 'albumartist', 'artist', 'audio_offset', 'bitrate', 'channels',
                      'comment', 'composer', 'disc', 'disc_total', 'duration', 'extra', 'filesize',
                      'filename', 'genre', 'samplerate', 'title', 'track', 'track_total', 'year'}


def run_cli(args):
    output = check_output('python -m tinytag ' + args, cwd=project_folder, shell=True)
    return output.decode('utf-8')


def file_size(filename):
    return os.stat(filename).st_size


@pytest.mark.xfail(raises=CalledProcessError)
def test_wrong_params():
    assert 'tinytag [options] <filename' in run_cli('-lol')


def test_print_help():
    assert 'tinytag [options] <filename' in run_cli('-h')
    assert 'tinytag [options] <filename' in run_cli('--help')


@pytest.mark.skipif(sys.platform == "win32",
                    reason="NamedTemporaryFile cant be reopened on windows")
def test_save_image_long_opt():
    temp_file = NamedTemporaryFile()
    assert file_size(temp_file.name) == 0
    run_cli('--save-image %s %s' % (temp_file.name, mp3_with_image))
    assert file_size(temp_file.name) > 0
    with open(temp_file.name, 'rb') as fh:
        image_data = fh.read(20)
        assert image_data.startswith(b'\xff')
        assert b'JFIF' in image_data


@pytest.mark.skipif(sys.platform == "win32",
                    reason="NamedTemporaryFile cant be reopened on windows")
def test_save_image_short_opt():
    temp_file = NamedTemporaryFile()
    assert file_size(temp_file.name) == 0
    run_cli('-i %s %s' % (temp_file.name, mp3_with_image))
    assert file_size(temp_file.name) > 0


@pytest.mark.skipif(sys.platform == "win32",
                    reason="NamedTemporaryFile cant be reopened on windows")
def test_save_image_bulk():
    temp_file = NamedTemporaryFile(suffix='.jpg')
    temp_file_no_ext = temp_file.name[:-4]
    assert file_size(temp_file.name) == 0
    run_cli('-i %s %s %s %s' % (temp_file.name, mp3_with_image, mp3_with_image, mp3_with_image))
    assert file_size(temp_file.name) == 0
    assert file_size(temp_file_no_ext + '00000.jpg') > 0
    assert file_size(temp_file_no_ext + '00001.jpg') > 0
    assert file_size(temp_file_no_ext + '00002.jpg') > 0


def test_meta_data_output_default_json():
    output = run_cli(mp3_with_image)
    data = json.loads(output)
    assert data
    assert set(data.keys()) == tinytag_attributes


def test_meta_data_output_format_json():
    output = run_cli('-f json ' + mp3_with_image)
    data = json.loads(output)
    assert data
    assert set(data.keys()) == tinytag_attributes


def test_meta_data_output_format_csv():
    output = run_cli('-f csv ' + mp3_with_image)
    lines = [line for line in output.split(os.linesep) if line]
    assert all(',' in line for line in lines)
    attributes = set(line.split(',')[0] for line in lines)
    assert set(attributes) == tinytag_attributes


def test_meta_data_output_format_tsv():
    output = run_cli('-f tsv ' + mp3_with_image)
    lines = [line for line in output.split(os.linesep) if line]
    assert all('\t' in line for line in lines)
    attributes = set(line.split('\t')[0] for line in lines)
    assert set(attributes) == tinytag_attributes


def test_meta_data_output_format_tabularcsv():
    output = run_cli('-f tabularcsv ' + mp3_with_image)
    header, line, rest = output.split(os.linesep)
    assert set(header.split(',')) == tinytag_attributes


@pytest.mark.xfail(raises=CalledProcessError)
def test_fail_on_unsupported_file():
    run_cli(bogus_file)


def test_fail_skip_unsupported_file_long_opt():
    run_cli('--skip-unsupported ' + bogus_file)


def test_fail_skip_unsupported_file_short_opt():
    run_cli('-s ' + bogus_file)
