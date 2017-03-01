# Utils

class Response(object):
    def __init__(self, mimetype=None, value=None):
        self.mimetype = mimetype or ""
        self.value = value or ""