class Session:
    def request(self, *args, **kwargs):  # pragma: no cover
        class Response:
            status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                return {}
        return Response()


def post(*args, **kwargs):  # pragma: no cover
    return Session().request("POST", *args, **kwargs)
