class Base:
    metadata = type("Meta", (), {"create_all": lambda self, engine: None})()


def declarative_base():
    return Base

