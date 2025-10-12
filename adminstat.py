import json
import os
from dotenv import load_dotenv

STATISTICS_FILE = "statistics.json"


def get_admin_uns():
    load_dotenv(override=True)
    ADMIN_UNS = [admin_id for admin_id in os.getenv('ADMIN_UNS', '').split(',')]
    return ADMIN_UNS


def set_first_stat():
    admstat = []
    for adm in get_admin_uns():
        admin = {
            'username': adm,
            'postcount': 0
        }
        admstat.append(admin)
    return admstat


def load_stat():
    try:
        with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
            return json.dump(set_first_stat(), f, ensure_ascii=False, indent=2)
   
        
def save_stat(stat):
    with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
            return json.dump(stat, f, ensure_ascii=False, indent=2)


def add_post_to_count(admin):
    stat = load_stat()
    for adm in stat:
        if adm['username'] == admin:
            adm['postcount'] += 1
    save_stat(stat)