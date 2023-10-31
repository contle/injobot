from pathlib import Path
from time import sleep
from tempfile import gettempdir
from os import remove
from configparser import SectionProxy

start_jobs_list = 'Jump to active job details'
end_job_description = 'How you match'

URL_end = '"'
tmp_path = Path(gettempdir()) / 'injobot'
if tmp_path.exists():
    print(f'{tmp_path=} path already exists.')
tmp_path.mkdir(exist_ok=True)

def load_text_file(file: Path) -> str:
    with open(file, 'r') as loaded_file:
        return loaded_file.read()

def load_html(file: Path, delete_comment: bool = True) -> str:
    if delete_comment:
        return load_text_file(file).replace('<!---->', '')
    return load_text_file(file)

def save_to_file(fn: Path, text: str):
    with open(fn, 'w') as source_file:
        source_file.write(text)

def paddle_with_whitespace(text: str, ws: str) -> str:
    return ws + text + ws

def get_first_index(s: str, sub: str, add_length: bool = False) -> int:
    position = s.find(sub)
    if position == -1:
        raise KeyError(f'{sub=} not found in text.')
    return position + add_length * len(sub)

def get_only_index(s: str, sub: str, add_length: bool = False) -> int:
    if s.count(sub) != 1:
        raise KeyError(f'{sub=} is {s.count(sub)} times in text instead of 1.')
    return s.find(sub) + add_length * len(sub)

def cut_between_unique(s: str, start: str, end: str):
    i_from, i_to = get_only_index(s, start, add_length=True), get_only_index(s, end)
    return s[i_from:i_to].strip()

def cut_between_first_ocurrencies(s: str, start: str, end: str) -> tuple[str, str]:
    '''
    returns tuple(variable, rest_of_string)
    '''
    start_cut = s[get_first_index(s, start, add_length=True):]
    end_index = get_first_index(start_cut, end)
    return start_cut[:end_index].strip(), start_cut[end_index:].strip()

def cut_until(s: str, sub: str) -> str:
    index = get_first_index(s, sub, add_length=True)
    return s[index:]

def cut_until_unique(s: str, sub: str) -> str:
    try:
        index = get_only_index(s, sub, add_length=True)
    except KeyError as e:
        print(f'get_only_index raised "{e}", probably the string is not unique as expected. Trying without unique.')
        index = get_first_index(s, sub, add_length=True)
    return s[index:].strip()

def countdown(seconds: int, silent: bool = False):
    while seconds > 0:
        seconds -= 1
        sleep(1)
        if not silent:
            print(f' {seconds}', end='\r')

debug_dir_name = 'debug_dir_name'
class TmpStore:
    def __init__(self, config_section: SectionProxy):
        self.debug_path = config_section[debug_dir_name]
        if self.debug_path:
            self.debug_path = tmp_path / self.debug_path
            self.debug_path.mkdir(exist_ok=True)

    def tmp_backup(self, text: str, filename: str):
        save_to_file(tmp_path / filename, text)

    def get_tmp_backup(self, filename: str) -> str:
        file = tmp_path / filename
        if file.is_file():
            return load_text_file(file)
        return ''

    def del_tmp_backup(self, filename: str):
        file = tmp_path / filename
        if file.is_file():
            remove(file)
        else:
            raise ValueError(f'file with {filename=} did not even exist.')

    def pop_from_tmp_list(self, filename: str):
        backuped_list = self.get_tmp_backup(filename).split('\n')
        backuped_list.pop(0)
        if backuped_list:
            self.tmp_backup('\n'.join(backuped_list), filename)
        else:
            self.del_tmp_backup(filename)

    def save_debug_file(self, filename: str, text: str):
        if self.debug_path:
            save_to_file(self.debug_path / filename, text)
