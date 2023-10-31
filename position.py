from yaml import dump, safe_load
from pathlib import Path
from subprocess import run, PIPE
from configparser import SectionProxy

from common import load_text_file, save_to_file, paddle_with_whitespace, tmp_path
from html_output_gen import generate_html, ExportType

job_location = 'location'
job_name = 'name'
job_company = 'company'
job_description = 'description'
job_type = 'type'
job_diff = 'diff'

position_type = dict[str, str]

class JobType:
    UNKOWN = ''
    ON_SITE = 'On-site'
    HYBRID = 'Hybrid'
    REMOTE = 'Remote'

job_types = {JobType.UNKOWN, JobType.ON_SITE, JobType.HYBRID, JobType.REMOTE}

# TODO do we need this?
def job_type_to_numeric(job_type: JobType) -> int:
    if job_type == JobType.ON_SITE:
        return 1
    if job_type == JobType.HYBRID:
        return 2
    if job_type == JobType.REMOTE:
        return 3
    return 0

def decode_config_list(list_as_str: str) -> list[str]:
    if (list_as_str[0] == '[') and (list_as_str[-1] == ']'):
        list_as_str = list_as_str[1:-1]
    return list_as_str.split(',')

use_name_filter = 'use_name_filter'
use_hybrid_filter = 'use_hybrid_filter'
use_if_remote_possible_filter = 'use_if_remote_possible_filter'
use_location_filter = 'use_location_filter'
hybrid_available_countries = 'hybrid_available_countries'
hybrid_unavailable_countries = 'hybrid_unavailable_countries'
hybrid_available_cities = 'hybrid_available_cities'
hybrid_unavailable_cities = 'hybrid_unavailable_cities'
class Position:
    def __init__(self,
                 job_id: int,
                 data_dir: Path,
                 config_section: SectionProxy,
                 details: position_type = None):
        self.job_id = job_id
        self.description_data_file = data_dir / f'{self.job_id}.descr'
        self._position_name = ''
        self._location = ''
        self._company = ''
        self._type = JobType.UNKOWN
        self._description = ''
        self._diff = ''
        if details:
            self.load_data(details)
        self.changed_in_this_session = False
        self.load_config(config_section)

    def load_config(self, config_section: SectionProxy,):
        self.use_name_filter = config_section.getboolean(use_name_filter)
        self.use_hybrid_filter = config_section.getboolean(use_hybrid_filter)
        self.use_if_remote_possible_filter = config_section.getboolean(use_if_remote_possible_filter)
        self.use_location_filter = config_section.getboolean(use_location_filter)
        self.use_name_filter = config_section.getboolean(use_name_filter)

        self.hybrid_available_countries = decode_config_list(config_section[hybrid_available_countries])
        self.hybrid_unavailable_countries = decode_config_list(config_section[hybrid_unavailable_countries])
        self.hybrid_available_cities = decode_config_list(config_section[hybrid_available_cities])
        self.hybrid_unavailable_cities = decode_config_list(config_section[hybrid_unavailable_cities])

    def __str__(self) -> str:
        return f'{self.job_id}:\n{self._position_name}"{self._company}"{self._type}:{self._location}'

    def load_data(self, details: position_type):
        self._location = details[job_location]
        self._type = details[job_type]
        self._position_name = details[job_name]
        self._company = details[job_company]
        if self._type not in job_types:
            raise ValueError(f'{self._type=} is invalid, should be one of {job_types}.')

    def name_filter(self):
        if (self._position_name == '') or (not self.use_name_filter):
            return True
        low = self._position_name.lower()
        contains_senior = low.find('senior') != -1
        contains_lead = low.find('lead ') != -1
        not_contains_senior_lead = not (contains_senior or contains_lead)
        contains_separator = (low.find('.') != -1) or (low.find(',') != -1) or \
                                (low.find('/') != -1) or (low.find('-') != -1)
        return not_contains_senior_lead  or contains_separator

    # hybrid_filters
    def list_filter(self,
                    text: str,
                    available: list[str],
                    unavailable: list[str],
                    whitespace_paddle: str = ' ') -> int:
        '''
        returns 1 if available, 0 if unavailable and -1 if unkown
        '''
        text = paddle_with_whitespace(text, whitespace_paddle)
        matched = []
        last_matched = ''
        for place in available + unavailable:
            if text.find(paddle_with_whitespace(place, whitespace_paddle)) != -1:
                last_matched = place
                matched.append(place)
        if len(matched) > 1:
            raise ValueError(f'All of {matched} are matched, please check')
        elif last_matched in unavailable:
            return 0
        if last_matched in available:
            return 1
        return -1

    def if_remote_possible_filter(self) -> bool:
        return (not use_if_remote_possible_filter) or (self.description.lower().find('remote') != -1)

    def contains_available_or_unkown(self, text: str, paddle_with_whitespace: str = ' ') -> bool:
        if not self.use_location_filter:
            return True

        country_filter = self.list_filter(text,
                                          self.hybrid_available_countries,
                                          self.hybrid_unavailable_countries,
                                          paddle_with_whitespace)
        if country_filter == 0:
            return False
        elif country_filter == 1:
            return True
        city_filter = self.list_filter(text,
                                       self.hybrid_available_cities,
                                       self.hybrid_unavailable_cities,
                                       paddle_with_whitespace)
        if city_filter == 0:
            return False
        elif city_filter == -1:
            print(f'neither filters are matched with {text=}')
        return True

    def hybrid_filter(self) -> bool:
        if (not self.use_hybrid_filter) or (self._type == JobType.UNKOWN) or (self._location == ''):
            return True
        is_remote = self._type == JobType.REMOTE
        is_hybrid = self._type == JobType.HYBRID
        hybrid_available = self.if_remote_possible_filter() or \
                           self.contains_available_or_unkown(self._location.lower())

        return is_remote or (is_hybrid and hybrid_available)

    def all_filters_succeed(self) -> bool:
        return self.name_filter() and self.hybrid_filter()

    def diff_simple(self, old_value: str, new_value: str) -> str:
        return f'an already working position is overwritten:\n"{old_value=}"\n"{new_value=}"\n'

    def diff_of_console(self, old_value: str, new_value: str) -> str:
        f1, f2 = tmp_path.parent / 'f1', tmp_path.parent / 'f2'
        save_to_file(f1, old_value)
        save_to_file(f2, new_value)
        diff = run(['diff', f1, f2], stdout=PIPE).stdout.decode('utf-8')
        return f'an already working position is overwritten:\n{diff}\n'

    def simple_change(self, old_value: str, new_value: str, attribute_name: str, diff: callable):
        if old_value == new_value:
            return
        if old_value != '' == new_value:
            raise ValueError(f'Overwriting {old_value=} with empty {new_value=}. Why?')
        if self.all_filters_succeed() and ('' != old_value):
            self._diff += diff(old_value, new_value)
        self.changed_in_this_session = True
        setattr(self, attribute_name, new_value)

# TODO is this even necessary?
    def strict_change(self, old_value: str, new_value: str) -> str:
        if new_value != old_value != '':
            raise ValueError(f'Overwriting {old_value=} with {new_value=}. Please check?')
        self.changed_in_this_session |= old_value != new_value
        return new_value

    @property
    def position_name(self) -> str:
        return self._position_name

    @position_name.setter
    def position_name(self, new_name: str):
        self.simple_change(self._position_name, new_name, '_position_name', self.diff_simple)

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, new_location: str):
        self.simple_change(self._location, new_location, '_location', self.diff_simple)

    @property
    def company(self):
        return self._company

    @company.setter
    def company(self, new_company: str):
        self.simple_change(self._company, new_company, '_company', self.diff_simple)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, new_type: str):
        self.simple_change(self._type, new_type, '_type', self.diff_simple)

    @property
    def description(self):
        if not self._description:
            if self.description_data_file.is_file():
                self._description = load_text_file(self.description_data_file)#.strip() # TODO no strip
        return self._description

    @description.setter
    def description(self, new_description: str):
        self.simple_change(self._description, new_description, '_description', self.diff_of_console)

    def as_dict(self) -> position_type:
        return {job_location: self.location,
                job_type: self.type,
                job_name: self._position_name,
                job_company: self._company}

    @property
    def diff(self):
        return f'\n{self._diff=}' if self._diff else ''

    def save_description(self):
        if self.description:
            save_to_file(self.description_data_file, self._description)

class Positions:
    def __init__(self, data_dir: Path, config_section: SectionProxy) -> None:
        self.config_section = config_section
        self.new_data_records = 0
        self.data_dir = data_dir
        self.data_index = self.data_dir / 'db.yaml'
        self.data: dict[int, Position] = {}
        if self.data_index.is_file():
            with open(self.data_index, 'r') as file:
                self.load_data(safe_load(file))
        else:
            print(f'no data file: using empty db.')
            data_dir.mkdir(exist_ok=True)

    def load_data(self, data: dict[int, position_type]):
        for job_id, details in data.items():
            self.data[job_id] = Position(job_id, self.data_dir, self.config_section, details)

    def count_changed_positions(self) -> int:
        count = 0
        for _, position in self.data.items():
            count += position.changed_in_this_session
        return count

    def save_data(self):
        data = {}
        for job_id, position in self.data.items():
            data[job_id] = position.as_dict()
            if position.changed_in_this_session:
                position.save_description()
        with open(self.data_index, 'w') as file:
            dump(data, file)
        print(f'{self.new_data_records} new records out of {self.count_changed_positions()} changed in this session.')

    def __getitem__(self, job_id: int) -> Position:
        if job_id not in self.data:
            self.new_data_records += 1
            self.data[job_id] = Position(job_id, self.data_dir, self.config_section)
        return self.data[job_id]

    def export_changed(self, export_html_path: Path):
        export_data: ExportType = {}
        for job_id, position in self.data.items():
            if position.all_filters_succeed() and position.changed_in_this_session:
                hash = (position.company, position.description + position.diff)
                value = (job_id, position.position_name, position.location, position.type)
                if hash in export_data:
                    export_data[hash].append(value)
                else:
                    export_data[hash] = [value]
        generate_html(export_html_path, export_data)
