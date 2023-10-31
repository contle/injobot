from common import cut_until_unique, get_first_index, cut_until, TmpStore
from browser_control import BrowserControl

job_description_cut_until = 'About the job'
job_description_start = '</h2>'
div_start = '<div>'
div_end = '</div>'

job_URL_start = 'https://www.linkedin.com/jobs/view/'
def get_job_page_URL(job_id: str) -> str:
    return f'{job_URL_start}{job_id}/'

def get_position_or_len(s: str, sub: str) -> int:
    try:
        return get_first_index(s, sub)
    except:
        return len(s)

def get_relevant_part(source: str) -> str:
    source_part = cut_until_unique(source, job_description_cut_until)
    return cut_until(source_part, job_description_start)

def get_div_perdiv_positions(source_part: str) -> tuple[int, int]:
    first_per_div_position = get_position_or_len(source_part, div_end)
    first_div_position = get_position_or_len(source_part, div_start)

    return first_div_position, first_per_div_position

class JobPageProcessor:
    def __init__(self, controller: BrowserControl, debug_store: TmpStore):
        self.controller = controller
        self.debug_store = debug_store

    def opening_or_closing_div(self, first_div_position: int, first_per_div_position: int) -> int:
        if first_div_position == first_per_div_position:
            raise ValueError('No more opening and closing div tags, something went wrong.')
        elif first_per_div_position > first_div_position:
            return +1
        else:
            return -1

    def get_job_description_counting_divs_len(self, source_part: str) -> int:

        original_len = len(source_part)
        div_count = 1
        while div_count > 0:
            first_per_div_position = get_position_or_len(source_part, div_end)
            first_div_position = get_position_or_len(source_part, div_start)

            div_count += self.opening_or_closing_div(first_div_position, first_per_div_position)

            cutting_until = min(first_div_position, first_per_div_position) + 1
            source_part = source_part[cutting_until:]

        return original_len - len(source_part) - 1

    def get_job_description(self, source: str = '', job_id: int = 0) -> str:
        if not source:
            self.controller.navigate(get_job_page_URL(job_id))
            source = self.controller.get_source()
        self.debug_store.save_debug_file(f'jp{job_id}.html', source)
        source_part = get_relevant_part(source)
        first_div_position, first_per_div_position = get_div_perdiv_positions(source_part)

        if first_per_div_position < first_div_position: # simple case
            return source_part[:first_per_div_position].strip()

        print('The description seems to contain div sections, trying to resolve anyway.')
        cutting_index = self.get_job_description_counting_divs_len(source_part)
        return self.trim_description(source_part[:cutting_index].strip())

    def trim_description(self, description: str):
        span_tag = '<span>'
        span_untag = '</span>'
        if (description[:len(span_tag)] == span_tag) and (description[-len(span_untag):] == span_untag):
            description = description[len(span_tag):-len(span_untag)].strip()
        return description
