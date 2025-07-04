class Session:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Exit the runtime context and close the session."""
        self.close()
        return False

    def execute(self, *args, **kwargs):  # pragma: no cover
        return []

    def scalars(self):  # pragma: no cover
        return self

    def all(self):  # pragma: no cover
        return []

    def add_all(self, items):  # pragma: no cover
        pass

    def add(self, item):  # pragma: no cover - simple stub
        pass

    def commit(self):  # pragma: no cover
        pass

    def close(self):  # pragma: no cover
        pass

    def get(self, model, identity):  # pragma: no cover - simple stub
        return None


def sessionmaker(bind=None):
    class _SessionFactory:
        def __call__(self):
            return Session()
    return _SessionFactory()

