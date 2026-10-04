"""The publisher must expose failed checks and still stop publication."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from publish_tinyppi import check, command
import publish_tinyppi


class CommandTests(unittest.TestCase):
    def test_failed_check_is_visible_and_fatal(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            with self.assertRaises(subprocess.CalledProcessError) as result:
                command(sys.executable, '-c',
                        "import sys; print('failed test details'); "
                        "print('failure traceback', file=sys.stderr); sys.exit(1)",
                        cwd=Path.cwd())
        self.assertEqual(result.exception.returncode, 1)
        self.assertIn('failed test details', output.getvalue())
        self.assertIn('failure traceback', output.getvalue())

    def test_success_remains_available_to_callers(self):
        result = command(sys.executable, '-c', "print('OK')", cwd=Path.cwd())
        self.assertEqual(result.stdout.strip(), 'OK')

    def test_successful_check_summary_is_visible(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            check(sys.executable, '-c', "print('all tests passed')", cwd=Path.cwd())
        self.assertIn('all tests passed', output.getvalue())

    def test_failed_tests_never_reach_either_channel(self):
        def fail_pytest(*args, **kwargs):
            if 'pytest' in args:
                raise subprocess.CalledProcessError(1, args)
            return subprocess.CompletedProcess(args, 0, '', '')

        with patch.object(publish_tinyppi, 'command', side_effect=fail_pytest):
            with patch.object(publish_tinyppi, 'publish') as publish:
                with self.assertRaises(subprocess.CalledProcessError):
                    publish_tinyppi.main()
                publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
