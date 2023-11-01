#!/usr/bin/env python

from configparser import ConfigParser
from sys import argv
from os import remove, system
from pathlib import Path

from common import tmp_path, TmpStore
from notif import NotificationProcessor
from browser_control import BrowserControl
from jobs_list import JobListingProcessor
from job_page import JobPageProcessor

def get_notif_links(controller: BrowserControl, tmp_store: TmpStore, links_filename: str = '') -> list[str]:
    file = tmp_path / links_filename
    if file.is_file():
        return tmp_store.get_tmp_backup(links_filename).split('\n')
    notification_processor = NotificationProcessor(controller)
    notif_links = notification_processor.load_notifs_get_links()
    tmp_store.tmp_backup('\n'.join(notif_links), links_filename)
    return notif_links

def main(export_html_path: Path, start_browser_only: bool = False):
    if export_html_path.is_file():
        remove(export_html_path)
        print('Export html found and deleted.')
    config = ConfigParser()
    config.read('injobot.ini')
    controller = BrowserControl(config['browser'])
    if start_browser_only:
        controller.navigate('http://linkedin.com')
        exit()
    tmp_store = TmpStore(config['debug'])
    links_filename = 'links'
    notif_links = get_notif_links(controller, tmp_store, links_filename)

    job_page_processor = JobPageProcessor(controller, tmp_store)
    job_listing = JobListingProcessor(controller, tmp_store, config['position'], job_page_processor)
    for index, notif_link in enumerate(notif_links):
        job_listing.process_all_pages(notif_link, index)
        job_listing.export_and_save(export_html_path)
        tmp_store.pop_from_tmp_list(links_filename)
    print('All notification links are gone, process complete.')

def wrap_main():
    export_html_path = tmp_path / 'export.html'
    try:
        if (len(argv) > 1) and (argv[1].lower() in {'login', 'setup', 'install'}):
            main(export_html_path, start_browser_only=True)
        else:
            main(export_html_path)
    except KeyboardInterrupt:
        print('Run stopped by user, opening export if exist.')
    system(f'xdg-open {export_html_path}')

wrap_main()