from utils.decorators import route_handlers

class Router():
    name = 'Router'
    description = 'Handles routes for all endpoints'

    def __init__(self):
        self.routes = route_handlers

    def route_request(self, request):
        action = request.get('action')
        uuid = request.get('uuid')
        value = request.get('value')

        if action in self.routes:
            response_data = self.routes[action](uuid, value)
            return {'action':action, 'value': response_data, 'status':'ok','uuid':uuid}
        else:
            return {'action': action, 'value': 'Unknown action', 'status': 'error', 'uuid': uuid}
