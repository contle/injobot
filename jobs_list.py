from pathlib import Path
from time import sleep
from configparser import SectionProxy

from common import cut_until, cut_between_first_ocurrencies, cut_between_unique, \
                   start_jobs_list, end_job_description, TmpStore
from browser_control import BrowserControl
from job_page import JobPageProcessor
from position import Positions, JobType

class EndOfListingException(Exception):
    pass

job_id_start = '/jobs/view/'
job_id_end = '/'

job_name_start = '">'
job_name_end = '</a>'

job_company_cut_until = 'job-card-container__primary-description'
job_company_start = '">'
job_company_end = '</span>'

job_location_cut_until = 'job-card-container__metadata-item'
job_location_start = '">'
job_location_end = '</li>'

class JobListingProcessor:
    def __init__(self, controller: BrowserControl, debug_store: TmpStore, config_section: SectionProxy):
        self.debug_store = debug_store
        self.controller = controller
        self.positions = Positions(Path('db'), config_section)

    def get_job_type(self, first_page_URL: str) -> str:
        is_remote = first_page_URL.find('f_WT=2') != -1
        is_hybrid = first_page_URL.find('f_WT=3') != -1
        is_onsite = first_page_URL.find('f_WT=1') != -1
        if is_remote + is_hybrid + is_onsite != 1:
            raise Exception(f'Job type not exact, {is_onsite=}, {is_hybrid=}, {is_remote=}, '
                            f'please check {first_page_URL=}.')
        if is_remote:
            return JobType.REMOTE
        if is_hybrid:
            return JobType.HYBRID
        return JobType.ON_SITE

    def initialize_new_data(self, job_list_type: str):
        self.new_data_job_type = job_list_type
        self.new_data_job_type_paranthesized = f'({job_list_type})'
        self.new_data_job_type_len = len(self.new_data_job_type_paranthesized)
        self.job_page_processor = JobPageProcessor(self.controller, self.debug_store)
        self.postprocess_job_ids = set()
      
    def process_all_pages(self,
                          first_page_URL: str,
                          notif_link_index: int,
                          postprocess_job_pages: bool = True):

        self.postprocess_job_pages = postprocess_job_pages
        self.initialize_new_data(self.get_job_type(first_page_URL))
        self.link_index = notif_link_index
        self.controller.navigate(first_page_URL)
        there_are_more_pages = True
        page_index = 1
        while there_are_more_pages:
            self.process_loaded_page()
            page_index += 1
            there_are_more_pages = self.controller.find_and_click_button('aria-label', f'Page {page_index}')
        self.postprocess()

    def postprocess(self):
        jobs_count_of_this_listing = len(self.postprocess_job_ids)
        print()
        for index, job_id in enumerate(self.postprocess_job_ids):
            print(f'\rprocessing {index + 1} / {jobs_count_of_this_listing}', end='')
            self.positions[job_id].description = self.job_page_processor.get_job_description(job_id=job_id)
        print()

    def separate_and_check_job_type(self, location: str) -> str:
        '''
        returns the location wthout the job type
        '''
        job_type = location[-self.new_data_job_type_len:]
        if job_type != self.new_data_job_type_paranthesized:
            raise ValueError(f'{location=} should contain [{job_type=}={self.new_data_job_type_paranthesized}]')
        return location[:-self.new_data_job_type_len].strip()

    def process_first_description(self, source_part: str, job_id: int):
        description = self.job_page_processor.get_job_description(source_part, job_id)
        self.positions[job_id].description = description

    def process_position(self, source_part: str) -> tuple[int, str]:
        '''
        returns a tuple containing
        - the job id
        - the rest of the source
        '''
        job_id_str, source_part = cut_between_first_ocurrencies(source_part, job_id_start, job_id_end)
        job_id = int(job_id_str)
        position = self.positions[job_id]

        job_name, source_part = cut_between_first_ocurrencies(source_part, job_name_start, job_name_end)
        try:
            source_part = cut_until(source_part, job_company_cut_until)
        except KeyError as e:
            raise EndOfListingException(f'reached end of listing, the first description comes {e}', job_id)
        position.position_name = job_name
        company, source_part = cut_between_first_ocurrencies(source_part, job_company_start, job_company_end)
        position.company = company

        source_part = cut_until(source_part, job_location_cut_until)
        location, source_part = cut_between_first_ocurrencies(source_part, job_location_start, job_location_end)
        location = self.separate_and_check_job_type(location)
        position.location = location
        position.type = self.new_data_job_type

        return job_id, source_part

    def process_job_listing(self):
        source_part = self.get_source_part()
        while source_part.find(job_id_start) != -1:
            try:
                job_id, source_part = self.process_position(source_part)
                self.postprocess_job_ids.add(job_id)
            except EndOfListingException as e:
                # print(e.args[0])
                sleep(1)
                job_id = e.args[1]
                self.process_first_description(source_part, job_id)
                self.postprocess_job_ids.discard(job_id)
                break

    def get_source_part(self) -> str:
        source_part = self.controller.get_source()
        try:
            source_part = cut_between_unique(source_part, start_jobs_list, end_job_description)
        except Exception as e:
            print(f'relevant part not found, {e}')
        return source_part

    def process_loaded_page(self):
        last_source = '#'
        source = self.controller.get_source()
        index = 0
        while source != last_source:
            self.debug_store.save_debug_file(f'jl{self.link_index}_{index}.html', source)
            index += 1
            last_source = source
            self.controller.scroll_list('jobs-search-results-list')
            sleep(1)
            source = self.controller.get_source()
        self.process_job_listing()

    def export_and_save(self, export_html_path: Path):
        self.positions.export_changed(export_html_path)
        self.positions.save_data()
