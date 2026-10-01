"""Focused contract checks for Linux /proc process identity parsing."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import process_identity
from process_identity import (
    _linux_process_start_identity,
    parse_linux_boot_time,
    parse_linux_process_stat,
    parse_linux_stat,
)


class LinuxProcessIdentityTests(unittest.TestCase):
    def temporary_proc(self):
        return tempfile.TemporaryDirectory(dir=os.environ['AGENT_RUNTIME_DIR'])

    def test_stat_uses_final_parenthesis_and_field_22(self):
        suffix = ['S'] + ['1'] * 18 + ['987654']
        raw = '4242 (worker ) with ) parens) ' + ' '.join(suffix)
        self.assertEqual(parse_linux_stat(raw, 4242), 987654)

    def test_stat_rejects_pid_mismatch_and_truncation(self):
        with self.assertRaises(ValueError):
            parse_linux_stat('4242 (worker) S ' + ' '.join(['1'] * 19), 7)
        with self.assertRaises(ValueError):
            parse_linux_stat('4242 (worker) S 1 2', 4242)

    def test_stat_lineage_fields_preserve_exact_pid_and_parent_group_session(self):
        suffix = ['S', '123', '4242', '4242'] + ['1'] * 15 + ['987654']
        self.assertEqual(parse_linux_process_stat(
            '4242 (worker ) with ) parens) ' + ' '.join(suffix), 4242),
            {'pid': 4242, 'ppid': 123, 'pgid': 4242, 'sid': 4242,
             'state': 'S', 'start_ticks': 987654})

    def test_boot_time_requires_one_valid_btime(self):
        self.assertEqual(parse_linux_boot_time('cpu 1\nbtime 1700000000\n'), 1700000000)
        for raw in ('cpu 1\n', 'btime x\n', 'btime 1\nbtime 2\n'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_linux_boot_time(raw)

    def test_identity_is_two_integer_protocol_values(self):
        with self.temporary_proc() as tmp:
            root = Path(tmp)
            (root / '4242').mkdir()
            suffix = ['S'] + ['1'] * 18 + ['987654']
            (root / '4242' / 'stat').write_text(
                '4242 (worker ) with ) parens) ' + ' '.join(suffix))
            (root / 'stat').write_text('btime 1700000000\n')
            identity = _linux_process_start_identity(4242, root)
        self.assertEqual(identity, [1700000000, 987654])
        self.assertTrue(all(type(value) is int for value in identity))

    def test_missing_pid_is_absent_but_missing_boot_metadata_is_unknown(self):
        with self.temporary_proc() as tmp:
            root = Path(tmp)
            with mock.patch.object(process_identity.sys, 'platform', 'linux'):
                with mock.patch.object(process_identity, '_linux_process_start_identity',
                                       side_effect=lambda pid: _linux_process_start_identity(pid, root)):
                    self.assertFalse(process_identity.process_matches(4242, [1, 2]))
                (root / '4242').mkdir()
                suffix = ['S'] + ['1'] * 18 + ['987654']
                (root / '4242' / 'stat').write_text(
                    '4242 (worker) ' + ' '.join(suffix))
                with self.assertRaises(FileNotFoundError):
                    process_identity._linux_process_start_identity(4242, root)

    def test_permission_and_malformed_identity_are_not_reported_as_absent(self):
        with self.temporary_proc() as tmp:
            root = Path(tmp)
            (root / '4242').mkdir()
            (root / '4242' / 'stat').write_text('not a proc stat record')
            (root / 'stat').write_text('btime 1700000000\n')
            with self.assertRaises(ValueError):
                process_identity._linux_process_start_identity(4242, root)
            with mock.patch.object(Path, 'read_text', side_effect=PermissionError('denied')):
                with self.assertRaises(PermissionError):
                    process_identity._linux_process_start_identity(4242, root)


if __name__ == '__main__':
    unittest.main()
