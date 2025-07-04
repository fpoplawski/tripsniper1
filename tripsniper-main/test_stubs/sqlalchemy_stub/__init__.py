class Column:
    def __init__(self, *args, **kwargs):
        pass

    def desc(self):
        return self

    def __le__(self, other):
        return self


class String: pass
class Float: pass
class Integer: pass
class Boolean: pass
class DateTime: pass


def create_engine(url):
    return object()


class _Select:
    def where(self, *args, **kwargs):
        return self
    def order_by(self, *args, **kwargs):
        return self
    def limit(self, *args, **kwargs):
        return self

def select(model):
    return _Select()

