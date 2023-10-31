from common import cut_until, cut_between_first_ocurrencies, URL_end
from browser_control import BrowserControl

notification_URL = 'https://www.linkedin.com/notifications/?filter=all'
source_trash_separator = 'Close jump menu'
search_URL_start = 'https://www.linkedin.com/jobs/search?savedSearchId='
saved_search_id_text = 'savedSearchId='

dayly_notif = 'a1698561926%2D'
weekly_notif = 'r604800'

class NotificationProcessor:
    def __init__(self, controller: BrowserControl, change_dayly_to_weekly_notif: bool = False):
        self.change_dayly_to_weekly_notif = change_dayly_to_weekly_notif
        self.controller = controller

    def conditioned_extend_day_to_week_search(self, link_part: str) -> str:
        if self.change_dayly_to_weekly_notif:
            if link_part.find(dayly_notif) == -1:
                raise ValueError(f'{link_part=} does not contain {dayly_notif=}')
            return link_part.replace(dayly_notif, weekly_notif)
        return link_part

    def load_notifs_get_links(self) -> list[str]:
        self.controller.navigate(notification_URL)
        source = cut_until(self.controller.get_source(), source_trash_separator)
        links = set()
        while source.find(saved_search_id_text) != -1:
            link_end, source = cut_between_first_ocurrencies(source, saved_search_id_text, URL_end)
            link_end = link_end.replace('&amp;', '&')
            link_end = self.conditioned_extend_day_to_week_search(link_end)
            links.add(search_URL_start + link_end)
        return list(links)
