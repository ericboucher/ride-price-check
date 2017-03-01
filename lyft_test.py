import requests
import queue
import copy
import json

# Testing On
from utils import Response
response = Response()
start_lat, start_lng, end_lat, end_lng = 37.7772, -122.4233, 70.7972, -122.4533

# Testing Off
# arguments = request.arguments
# start_lat = float(arguments['start_lat'][0])
# start_lng = float(arguments['start_lng'][0])
# end_lat = float(arguments['end_lat'][0])
# end_lng = float(arguments['end_lng'][0])

response_value = {}

# LYFT
AUTH_TOKEN_LYFT = 'gAAAAABYrQFjeFv9D56yv-ABqwWjI0dt0Q47spVEP3g1N-juBNozx4QcX8pXpi72Ak0_z0MEIokvmR7r7DQd4p' + \
                  '2-CdBKj_L4ntTDDf888YodLH0mV8yJhsy3KM6Maef3Nh53Ah3DPTP31wPRn95lcCGyglKHzN-VYsaJ3Jqy3uqm' + \
                  'U8juHHfGk_Q='

HEADERS_LYFT = {"Authorization": "Bearer {}".format(AUTH_TOKEN_LYFT)}
ENDPOINT = 'https://api.lyft.com/v1/'
LYFT_PRICE_MULTIPLIER = 1.0/100
request_lyft = ENDPOINT + "cost?start_lat=%.2f&start_lng=%.2f&end_lat=%.2f&end_lng=%.2f"
lyft_deeplink = "lyft://ridetype?id=%s&pickup[latitude]=%.2f&pickup[longitude]=%.2f" +\
                "&destination[latitude]=%.2f&destination[longitude]=%.2f"

# UBER
AUTH_TOKEN_UBER = "rrl5HHVjIt8xnY3AE3VlQW2W6SkpIkvhQQivYbI5"
HEADERS_UBER = {"Authorization": "Token {}".format(AUTH_TOKEN_UBER),
                "Accept-Language": "en_US",
                "Content-Type": "application/json"}

ENDPOINT_UBER = 'https://api.uber.com/v1.2/'
UBER_PRICE_MULTIPLIER = 1.0
request_uber = ENDPOINT_UBER + \
               "estimates/price?start_latitude=%.2f&start_longitude=%.2f&end_latitude=%.2f&end_longitude=%.2f"
uber_deeplink = "https://m.uber.com/ul/?client_id=<CLIENT_ID>&action=setPickup&" +\
                "pickup[latitude]=%.2f&pickup[longitude]=%.2f" + \
                "&dropoff[latitude]=%.2f&dropoff[longitude]=%.2f&" +\
                "product_id=%s"


class PriceResult(object):
    """docstring for ClassName"""
    def __init__(self, company, ride_type, price, ride_type_id=None):
        self.company = company
        self.ride_type = ride_type
        self.price = price
        self.ride_type_id = ride_type_id

    def __str__(self):
        return "%s %s %s" % (self.company,
                             self.ride_type,
                             self.price)

    def __repr__(self):
        return "%s %s %s" % (self.company,
                             self.ride_type,
                             self.price)

    def __lt__(self, other):
        selfPriority = self.price
        otherPriority = other.price
        return selfPriority < otherPriority


def merge_queues(queue_a, queue_b):
    while not queue_b.empty():
        queue_a.put(queue_b.get())
    return queue_a


def read_queue(queue):
    temp_queue = copy.copy(queue)
    while not temp_queue.empty() and not temp_queue.qsize() == 0:
        element = temp_queue.get(block=False)
        print(element)


def get_request_format(company):
    if company.lower() == 'lyft':
        return {'request': request_lyft,
                'headers': HEADERS_LYFT,
                'response_level_1': 'cost_estimates',
                'company': 'Lyft',
                'ride_type': 'ride_type',
                'price': 'estimated_cost_cents_max',
                'multiplier': LYFT_PRICE_MULTIPLIER,
                'ride_type_id': 'na'}
    elif company.lower() == 'uber':
        return {'request': request_uber,
                'headers': HEADERS_UBER,
                'response_level_1': 'prices',
                'company': 'Uber',
                'ride_type': 'localized_display_name',
                'price': 'high_estimate',
                'multiplier': UBER_PRICE_MULTIPLIER,
                'ride_type_id': 'product_id'}


def get_prices(company, start_lat, start_lng, end_lat, end_lng):
    global response
    temp_result_queue = queue.PriorityQueue()
    request_info = get_request_format(company)
    request = request_info['request'] % (start_lat, start_lng, end_lat, end_lng)
    response_content = requests.get(request, headers=request_info['headers'])

    for cost_estimate in response_content.json()[request_info['response_level_1']]:
        try:
            result = PriceResult(request_info['company'],
                                 cost_estimate[request_info['ride_type']],
                                 cost_estimate[request_info['price']] * request_info['multiplier'],
                                 cost_estimate.get(request_info['ride_type_id'], None))
            temp_result_queue.put((result.price, result))
        except TypeError:
            pass

    return temp_result_queue


def create_response_json(start_lat, start_lng, end_lat, end_lng, best_price):
    response_value['input_data'] = "Start %s, %s - End %s, %s" % (start_lat, start_lng, end_lat, end_lng)
    response_value['cheapest_company'] = best_price.company
    response_value['cheapest_price'] = best_price.price
    response_value['ride_type'] = best_price.ride_type
    response_value['ride_type_id'] = getattr(best_price, 'ride_type_id', None)

    if best_price.company.lower() == 'uber':
        response_value['deep_link'] = uber_deeplink % (start_lat, start_lng, end_lat, end_lng,
                                                       best_price.ride_type_id)
    elif best_price.company.lower() == 'lyft':
        response_value['deep_link'] = lyft_deeplink % (best_price.ride_type,
                                                       start_lat, start_lng, end_lat, end_lng)
    response_value['response_status'] = 'ok'


if __name__ == '__main__':
    try:
        # Look for options and order them
        result_queue = queue.PriorityQueue()
        for company in ['uber', 'lyft']:
            result_queue = merge_queues(result_queue, get_prices(company, start_lat, start_lng, end_lat, end_lng))

        element = result_queue.get(block=False)
        json_response = create_response_json(start_lat, start_lng, end_lat, end_lng, element[1])
        result_queue.put(element)
    except Exception as e:
        response_value['response_status'] = 'error'
        response_value['error_message'] = repr(e)
    # read_queue(result_queue)
    print(response_value)
    response.value = json.dumps(response_value)
    print(response.value)
