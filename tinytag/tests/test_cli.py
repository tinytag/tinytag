# SPDX-FileCopyrightText: 2020-2024 tinytag Contributors
# SPDX-License-Identifier: MIT

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=missing-module-docstring

import json
import os

from subprocess import check_output, CalledProcessError, STDOUT
from sys import executable
from tempfile import NamedTemporaryFile
from unittest import TestCase

PROJECT_FOLDER = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SAMPLE_FOLDER = os.path.join(PROJECT_FOLDER, 'tinytag', 'tests', 'samples')
MP3_WITH_IMG = os.path.join(SAMPLE_FOLDER, 'image-text-encoding.mp3')
BOGUS_FILE = os.path.join(SAMPLE_FOLDER, 'there_is_no_such_ext.bogus')
TINYTAG_ATTRIBUTES = {
    'album', 'albumartist', 'artist', 'bitdepth', 'bitrate',
    'channels', 'comment', 'composer', 'disc', 'disc_total', 'duration',
    'filesize', 'filename', 'genre', 'samplerate', 'title', 'track',
    'track_total', 'year'
}


class TestCLI(TestCase):

    @staticmethod
    def run_cli(args: str) -> str:
        debug_env = str(os.environ.pop("TINYTAG_DEBUG", None))
        output = check_output(
            f'{executable} -m tinytag ' + args, cwd=PROJECT_FOLDER,
            shell=True, stderr=STDOUT)
        if debug_env:
            os.environ["TINYTAG_DEBUG"] = debug_env
        return output.decode('utf-8')

    def test_wrong_params(self) -> None:
        with self.assertRaises(CalledProcessError) as excinfo:
            self.run_cli('-lol')
        output = excinfo.exception.stdout.strip()
        self.assertEqual(
            output, b"-lol: [Errno 2] No such file or directory: '-lol'")

    def test_print_help(self) -> None:
        self.assertIn('tinytag [options] <filename', self.run_cli('-h'))
        self.assertIn('tinytag [options] <filename', self.run_cli('--help'))

    def test_save_image_long_opt(self) -> None:
        with NamedTemporaryFile() as temp_file:
            self.assertEqual(os.path.getsize(temp_file.name), 0)
        self.run_cli(f'--save-image {temp_file.name} {MP3_WITH_IMG}')
        self.assertGreater(os.path.getsize(temp_file.name), 0)
        with open(temp_file.name, 'rb') as file_handle:
            image_data = file_handle.read(20)
            self.assertTrue(image_data.startswith(b'\xff'))
            self.assertIn(b'JFIF', image_data)

    def test_save_image_short_opt(self) -> None:
        with NamedTemporaryFile() as temp_file:
            self.assertEqual(os.path.getsize(temp_file.name), 0)
        self.run_cli(f'-i {temp_file.name} {MP3_WITH_IMG}')
        self.assertGreater(os.path.getsize(temp_file.name), 0)

    def test_save_image_bulk(self) -> None:
        temp_name = None
        with NamedTemporaryFile(suffix='.jpg') as temp_file:
            temp_name = temp_file.name
            temp_name_no_ext = temp_name[:-4]
            self.assertEqual(os.path.getsize(temp_name), 0)
        self.run_cli(
            f'-i {temp_name} {MP3_WITH_IMG} {MP3_WITH_IMG} {MP3_WITH_IMG}')
        self.assertFalse(os.path.isfile(temp_name))
        self.assertGreater(os.path.getsize(temp_name_no_ext + '00000.jpg'), 0)
        self.assertGreater(os.path.getsize(temp_name_no_ext + '00001.jpg'), 0)
        self.assertGreater(os.path.getsize(temp_name_no_ext + '00002.jpg'), 0)

    def test_meta_data_output_default_json(self) -> None:
        output = self.run_cli(MP3_WITH_IMG)
        data = json.loads(output)
        self.assertTrue(data)
        self.assertTrue(set(data.keys()).issubset(TINYTAG_ATTRIBUTES))

    def test_meta_data_output_format_json(self) -> None:
        output = self.run_cli('-f json ' + MP3_WITH_IMG)
        data = json.loads(output)
        self.assertTrue(data)
        self.assertTrue(set(data.keys()).issubset(TINYTAG_ATTRIBUTES))

    def test_meta_data_output_format_csv(self) -> None:
        output = self.run_cli('-f csv ' + MP3_WITH_IMG)
        lines = [line for line in output.split(os.linesep) if line]
        self.assertTrue(all(',' in line for line in lines))
        attributes = set(line.split(',')[0] for line in lines)
        self.assertTrue(set(attributes).issubset(TINYTAG_ATTRIBUTES))

    def test_meta_data_output_format_tsv(self) -> None:
        output = self.run_cli('-f tsv ' + MP3_WITH_IMG)
        lines = [line for line in output.split(os.linesep) if line]
        self.assertTrue(all('\t' in line for line in lines))
        attributes = set(line.split('\t')[0] for line in lines)
        self.assertTrue(set(attributes).issubset(TINYTAG_ATTRIBUTES))

    def test_meta_data_output_format_tabularcsv(self) -> None:
        output = self.run_cli('-f tabularcsv ' + MP3_WITH_IMG)
        header, _line, _rest = output.split(os.linesep)
        self.assertTrue(set(header.split(',')).issubset(TINYTAG_ATTRIBUTES))

    def test_meta_data_output_format_invalid(self) -> None:
        output = self.run_cli('-f invalid ' + MP3_WITH_IMG)
        self.assertFalse(output)

    def test_fail_on_unsupported_file(self) -> None:
        with self.assertRaises(CalledProcessError):
            self.run_cli(BOGUS_FILE)

    def test_fail_skip_unsupported_file_long_opt(self) -> None:
        self.run_cli('--skip-unsupported ' + BOGUS_FILE)

    def test_fail_skip_unsupported_file_short_opt(self) -> None:
        self.run_cli('-s ' + BOGUS_FILE)
