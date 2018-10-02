"""A module to query Transport NSW (Australia) departure times."""
from datetime import timedelta, datetime
import requests

ATTR_STOP_ID = 'stopid'
ATTR_ROUTE = 'route'
ATTR_DUE_IN = 'due'
ATTR_DELAY = 'delay'
ATTR_REALTIME = 'realtime'


class TransportNSW(object):
    """The Class for handling the data retrieval."""

    def __init__(self):
        """Initialize the data object."""
        self.stopid = None
        self.route = None
        self.apikey = None
        self.info = [{
            ATTR_ROUTE: None,
            ATTR_DUE_IN: 'n/a',
            ATTR_DELAY: 'n/a',
            ATTR_REALTIME: 'n/a',
            }]

    def get_departures(self, stopid, route, apikey):
        """Get the latest data from Transport NSW."""
        self.stopid = stopid
        self.route = route
        self.apikey = apikey

        #Build the URL including the STOPID and the API key
        url = \
            'https://api.transport.nsw.gov.au/v1/tp/departure_mon?' \
            'outputFormat=rapidJSON&coordOutputFormat=EPSG%3A4326&' \
            'mode=direct&type_dm=stop&name_dm=' \
            + self.stopid \
            + '&departureMonitorMacro=true&TfNSWDM=true&version=10.2.1.42'
        auth = 'apikey ' + self.apikey
        header = {'Accept': 'application/json', 'Authorization': auth}

        response = requests.get(url, headers=header, timeout=10)

        # If there is no valid request, set to default response
        if response.status_code != 200:
            print("Error with the request sent")
            #print response.status_code
            self.info = [{
                ATTR_ROUTE: self.route,
                ATTR_DUE_IN: 'n/a',
                ATTR_DELAY: 'n/a',
                ATTR_REALTIME: 'n/a',
                }]
            return self.info

        # Parse the result as a JSON object
        result = response.json()
        #print(result)

        # If there is no stop events for the query, set to default response
        try:
            result['stopEvents']
        except KeyError:
            #print("No stop events for this query")
            self.info = [{
                ATTR_ROUTE: self.route,
                ATTR_DUE_IN: 'n/a',
                ATTR_DELAY: 'n/a',
                ATTR_REALTIME: 'n/a',
                }]
            return self.info

        # Set timestamp format and variables
        fmt = '%Y-%m-%dT%H:%M:%SZ'
        maxresults = 3
        monitor = []

        if self.route != '':
            # Find the next stop events for a specific route
            for i in range(len(result['stopEvents'])):
                number = ''
                planned = ''
                estimated = ''
                due = 0
                delay = 0
                realtime = 'n'

                number = result['stopEvents'][i]['transportation']['number']
                if number == self.route:
                    planned = datetime.strptime(result['stopEvents'][i]
                                                ['departureTimePlanned'], fmt)
                    estimated = planned
                    if 'isRealtimeControlled' in result['stopEvents'][i]:
                        realtime = 'y'
                        estimated = datetime.strptime(result['stopEvents'][i]
                                                      ['departureTimeEstimated'], fmt)
                    if estimated > datetime.utcnow():
                        due = self.get_due(estimated)
                        delay = self.get_delay(planned, estimated)
                        monitor.append([
                            number,
                            due,
                            delay,
                            planned,
                            estimated,
                            realtime,
                            ])

                    if len(monitor) >= maxresults:
                        # We found enough results, lets stop
                        break
        else:
            # No route defined, find any route leaving next
            for i in range(0, maxresults):
                number = ''
                planned = ''
                estimated = ''
                due = 0
                delay = 0
                realtime = 'n'

                number = result['stopEvents'][i]['transportation']['number']
                planned = datetime.strptime(result['stopEvents'][i]
                                            ['departureTimePlanned'], fmt)
                estimated = planned
                if 'isRealtimeControlled' in result['stopEvents'][i]:
                    realtime = 'y'
                    estimated = datetime.strptime(result['stopEvents'][i]
                                                  ['departureTimeEstimated'], fmt)

                # Only deal with future leave times
                if estimated > datetime.utcnow():
                    due = self.get_due(estimated)
                    delay = self.get_delay(planned, estimated)

                    monitor.append([
                        number,
                        due,
                        delay,
                        planned,
                        estimated,
                        realtime,
                        ])

        if monitor:
            self.info = [{
                ATTR_ROUTE: monitor[0][0],
                ATTR_DUE_IN: monitor[0][1],
                ATTR_DELAY: monitor[0][2],
                ATTR_REALTIME: monitor[0][5],
                }]
            return self.info
        else:
            # No stop events for this route
            self.info = [{
                ATTR_ROUTE: self.route,
                ATTR_DUE_IN: 'n/a',
                ATTR_DELAY: 'n/a',
                ATTR_REALTIME: 'n/a',
                }]
            return self.info

    def get_due(self, estimated):
        """Min till next leave event"""
        due = 0
        due = round((estimated - datetime.utcnow()).seconds / 60)
        return due

    def get_delay(self, planned, estimated):
        """Min of delay on planned departure"""
        delay = 0
        if estimated >= planned:
            delay = round((estimated - planned).seconds / 60)
        else:
            delay = round((planned - estimated).seconds / 60) * -1
        return delay
