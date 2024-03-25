import tempfile
import time
import unittest
from sys import platform

from app.error_handling import ShellCommandError
from app.utils import convert_encoding, to_string, run_shell_command, working_directory


class ShellTest(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_run_shell_command_raises(self):
        self.assertRaises(ShellCommandError, lambda: run_shell_command(12315, raise_exception=True))
        self.assertRaises(ShellCommandError,
                          lambda: run_shell_command(bytearray(b'git add example.txt'), raise_exception=True))
        if platform == "linux" or platform == "linux2":
            self.assertRaises(ShellCommandError,
                              lambda: run_shell_command(['notepad', 'example.txt'], raise_exception=True))
        elif platform == 'win32':
            self.assertRaises(ShellCommandError,
                              lambda: run_shell_command(['touch', 'example.txt'], raise_exception=True))

    def test_run_shell_command_list(self):
        with tempfile.TemporaryDirectory(dir='tmp') as tmp_dir_name:
            # конструкция для перехода в каталог для обработки файлов
            with working_directory(tmp_dir_name):
                msg, ok = run_shell_command(['git', 'init'])
                self.assertEquals(msg[:36], 'Initialized empty Git repository in ')
                self.assertEquals(ok, 0)

                if platform == "linux" or platform == "linux2":
                    msg, ok = run_shell_command('touch example.txt')
                    self.assertEquals(msg, "")
                    self.assertEquals(ok, 0)
                elif platform == 'win32':
                    f = open('example.txt', 'w')
                    f.close()

                msg, ok = run_shell_command('git add example.txt')
                self.assertEquals(msg, "")
                self.assertEquals(ok, 0)

                _, ok = run_shell_command(
                    ['git', 'commit', '-m', f'"Uploaded by SUM integration service {time.ctime()}"'])
                self.assertEquals(ok, 0)

                msg, ok = run_shell_command(f'git remote add sshtmporiginexmaple ssh://root@192.168.1.14:22/'
                                            f'superkey/supername.git')
                self.assertEquals(msg, "")
                self.assertEquals(ok, 0)

                msg, ok = run_shell_command(
                    [f'git', 'push', f'sshtmporiginexmaple', f'master:refs/heads/tmpbranchexmaple'])
                self.assertEquals(msg[:42], 'ssh: connect to host 192.168.1.14 port 22:')
                self.assertEquals(ok, 128)

                msg, ok = run_shell_command([f'git', 'push', f'sshtmporiginexmaple', f':tmpbranchexmaple'])
                self.assertEquals(msg[:42], 'ssh: connect to host 192.168.1.14 port 22:')
                self.assertEquals(ok, 128)

                msg, ok = run_shell_command([f'git', 'remote', 'remove', f'sshtmporiginexmaple'])
                self.assertEquals(msg, "")
                self.assertEquals(ok, 0)

                msg, ok = run_shell_command(['git', 'rm', 'example.txt'])
                self.assertEquals(msg, "rm 'example.txt'\n")
                self.assertEquals(ok, 0)

                _, ok = run_shell_command(['git', 'commit', '-m', f'"Remove example.txt at {time.ctime()}"'])
                self.assertEquals(ok, 0)

                msg, ok = run_shell_command(12315)
                self.assertEquals(msg, "Can't convert arguments to list or arguments is not list (type: <class 'int'>)")
                self.assertEquals(ok, -2)

                msg, ok = run_shell_command(bytearray(b'git add example.txt'))
                self.assertEquals(msg, "Can't convert arguments to list or arguments is not list (type: <class "
                                       "'bytearray'>)")
                self.assertEquals(ok, -2)

    def test_to_string(self):
        byte_string = b'Hello my friend'
        result = to_string(byte_string)
        self.assertEquals('Hello my friend', result)

    def test_convert_encoding(self):
        string2 = 'Привет. Просто текст на русском языке'

        encoded_string2 = string2.encode('utf-8')
        decoded_string2 = convert_encoding(encoded_string2)
        self.assertEquals(string2, decoded_string2)

        encoded_string2 = string2.encode('cp1251')
        decoded_string2 = convert_encoding(encoded_string2)
        self.assertEquals(string2, decoded_string2)

        encoded_string3 = string2.encode('cp866')
        decoded_string3 = convert_encoding(encoded_string3)
        self.assertEquals(string2, decoded_string3)

    def tearDown(self) -> None:
        pass


if __name__ == "__main__":
    unittest.main()
