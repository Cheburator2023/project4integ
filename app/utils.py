import datetime
import os
import random
import re
import shlex
import string
import subprocess
from contextlib import contextmanager
from distutils.util import strtobool
from hashlib import sha256
from sys import platform
from traceback import print_exc
from typing import List, Optional, Union

import cchardet

from app.error_handling import ShellCommandError

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DATE_TIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"
VERSION_DATE_TIME_FORMAT = "%Y%m%d%H%M%S%f"  # "(4:год)(2:месяц)(2:день)(2:час)(2:минута)(2:секунда)(6:микросекунда)"


def remove_cyrillic(word: str) -> str:
    if re.search(r"[а-яА-ЯёЁ]", word):
        symbols = (
            "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",
            "abvgdeejzijklmnoprstufhzcss_y_euaABVGDEEJZIJKLMNOPRSTUFHZCSS_Y_EUA",
        )
        tr = {ord(a): ord(b) for a, b in zip(*symbols)}
        return word.translate(tr)
    else:
        return word


def get_current_datetime(date_time_format: str = DATE_TIME_FORMAT) -> str:
    """Return datetime in string with date_time_format"""

    return f"{datetime.datetime.now():{date_time_format}}"


def get_rnd_sfx(length: int = 7) -> str:
    """Generate random sequence of uppercase latin letters and numbers of length"""

    return "".join(
        random.choices(string.ascii_uppercase + string.digits, k=length)
    )


@contextmanager
def working_directory(directory: str) -> None:
    """Context manager for working with temporary directory path"""

    prev_cwd = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def get_hash_from_string(data: str) -> str:
    if not data:
        return ""
    return sha256(data.encode("utf-8")).hexdigest()


def decode_bytes(data: Optional[bytes]) -> Optional[str]:
    if data is not None:
        data = data.decode("utf-8")
    return data


def calc_hexdigest(data: str) -> str:
    if not data:
        return ""
    return sha256(data.encode("utf-8")).hexdigest()


def convert_encoding(input_value):
    tmp_value = input_value
    try:
        chardet_result = cchardet.detect(input_value)
    except TypeError:
        print_exc()
        return tmp_value
    encoding = chardet_result.get('encoding', 'utf-8')
    try:
        tmp_value = input_value.decode(encoding)
    except Exception:
        print_exc()
    return tmp_value


def to_string(input_value: Union[str, bytes]) -> str:
    """Convert bytes to str"""
    if not input_value:
        return ''
    if isinstance(input_value, str):
        return input_value
    tmp_value = convert_encoding(input_value)
    return tmp_value


def run_shell_command(args: Union[List[str], str], raise_exception: bool = False) -> (str, int):
    """Running shell command in python code

    input formats can be like list of strings or single string
    """
    error_code = 0

    if isinstance(args, list):
        arguments = args
    elif isinstance(args, str):
        arguments = shlex.split(args)
    else:
        args_type = type(args)
        error_message = f"Can't convert arguments to list or arguments is not list (type: {args_type})"
        if raise_exception:
            raise ShellCommandError(error_message)
        return error_message, -2
    in_shell = False
    if platform == 'win32':
        in_shell = True
    try:
        out_bytes = subprocess.check_output(args=arguments, stderr=subprocess.STDOUT, shell=in_shell)
    except FileNotFoundError as e:
        out_bytes = f'{e.strerror}, args={str(arguments)}'
        error_code = e.errno
    except subprocess.CalledProcessError as e:
        out_bytes = e.output
        error_code = e.returncode
    except Exception as e:
        out_bytes = str(e)
        error_code = -1
    out_str = to_string(out_bytes)
    if raise_exception:
        raise ShellCommandError(f"Message: {out_str} Code: {error_code}")
    return out_str, error_code


def convert_to_bytes(input_value: str) -> int:
    value = str(input_value).strip().lower()
    if value == 'none':
        raise ValueError

    try:
        return int(value)
    except ValueError:
        pass
    maps = {
        'kb': 1 << 10,
        'mb': 1 << 20,
        'gb': 1 << 30
    }
    for size in maps:
        if value.endswith(size):
            units = value.removesuffix(size).strip()
            if units == '':
                units = 1
            units = int(units)  # on error raise ValueError
            return int(units * maps[size])
    raise ValueError


def get_version_date_time() -> str:
    return get_current_datetime(VERSION_DATE_TIME_FORMAT)


def str_to_datetime(input_value: str, date_time_format) -> datetime:
    return datetime.datetime.strptime(input_value, date_time_format)


def join_url(pieces: List[str]) -> str:
    """Concat strings with '/'.
    truncate '/' from begin and of string pieces
    """
    return '/'.join(s.strip('/') for s in pieces)


def str_to_bool(value: str) -> bool:
    return bool(strtobool(str(value)))
