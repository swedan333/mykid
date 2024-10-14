import requests
import re
import json
from datetime import datetime, timedelta

class MyKidAPI:
    def __init__(self, phone, password):
        self.phone = phone
        self.password = password
        self.session = requests.Session()
        self.csrf_token = None
        self.base_url = 'https://mykid.no'

    def validate_credentials(self):
        try:
            return self.login()
        except Exception:
            return False

    def login(self):
        # Fetch the login page to get CSRF token and cookies
        login_page_url = f'{self.base_url}/nb/logg_inn'
        response = self.session.get(login_page_url)
        content = response.text

        # Extract CSRF token
        token_matches = re.findall(r'_csrf_token" value="([^"]+)"', content)
        if not token_matches:
            return False
        self.csrf_token = token_matches[-1]

        # Update session cookies
        self.session.cookies.set('landingpage_language', 'nb')
        self.session.cookies.set('landingpage_prefix', '47')

        # Prepare login data
        login_url = f'{self.base_url}/forside/forside/login'
        login_data = {
            '_csrf_token': self.csrf_token,
            'pp': '47',
            'm': self.phone,
            'p': self.password
        }

        # Perform login
        login_response = self.session.post(login_url, data=login_data)
        login_result = login_response.json()

        return login_result.get('status') == 'ok'

    def fetch_events(self, start_date, end_date):
        if not self.csrf_token:
            if not self.login():
                return []

        # Access 'foreldre' page to update CSRF token
        foreldre_url = f'{self.base_url}/foreldre'
        foreldre_response = self.session.get(foreldre_url)
        foreldre_content = foreldre_response.text

        csrf_token_match = re.search(r'_csrf_token" content="([^"]+)"', foreldre_content)
        if csrf_token_match:
            self.csrf_token = csrf_token_match.group(1)
        else:
            return []

        # Extract children
        children_matches = re.findall(
            r'<a href="_ajax/avdelinger/bytt_barn/(\d+)/foreldre" class="([^"]*)"[^>]*>\s*<img[^>]*>\s*<span class="dep-name">\s*([^<]*)',
            foreldre_content
        )

        children = []
        for match in children_matches:
            child_id, selected_class, name = match
            selected = 'selected' in selected_class
            children.append({
                'id': child_id,
                'selected': selected,
                'name': name.strip()
            })

        # Fetch calendar data
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        self.session.headers.update(headers)

        data = {
            'from': start_date,
            'to': end_date,
            '_csrf': self.csrf_token
        }

        cal = []
        meals = []

        # Get selected child
        selected_child = next((c for c in children if c['selected']), None)
        if selected_child is None:
            return []

        # Fetch calendar data for the selected child
        calendar_url = f'{self.base_url}/_ajax/calendar/fetch_calendar_data'
        calendar_response = self.session.post(calendar_url, data=data)
        child_calendar = calendar_response.json()

        # Filter out birthday events
        child_calendar = [entry for entry in child_calendar if entry.get('class') != 'birthday']

        # Separate meals and calendar events
        for entry in child_calendar:
            if entry.get('avdeling_id') == '-1':
                meals.append(entry)
            else:
                entry['name'] = selected_child['name']
                cal.append(entry)

        # Fetch calendar data for the rest of the children
        for child in [c for c in children if not c['selected']]:
            # Switch to the child's calendar
            switch_child_url = f"{self.base_url}/_ajax/avdelinger/bytt_barn/{child['id']}/kalender"
            self.session.get(switch_child_url)

            # Fetch the calendar data
            calendar_response = self.session.post(calendar_url, data=data)
            child_calendar = calendar_response.json()
            child_calendar = [entry for entry in child_calendar if entry.get('class') != 'birthday']

            for entry in child_calendar:
                if entry.get('avdeling_id') != '-1':
                    entry['name'] = child['name']
                    cal.append(entry)

        # Format events
        cal_output = [
            {
                'date_from': event['date_from'],
                'time_from': event['time_from'],
                'time_to': event['time_to'],
                'title': event['title'],
                'description': event['description'],
                'name': event['name']
            }
            for event in cal
        ]

        return cal_output
