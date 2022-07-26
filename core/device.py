

class RemoteDevice:
    open: bool = False
    name: str = None

    def __init__(self, name: str):
        self.name = name

    def close(self):
        pass

    def spin(self):
        pass

    def watch_update(self, path: str, val):
        pass
