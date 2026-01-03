# simple_approximate_map.py
class SimpleApproximateMap:
    def __init__(self):
        self.map = {}
        self.epoch = 0

    def clear(self):
        self.map.clear()
        self.epoch += 1

    def next_epoch(self):
        self.epoch += 1

    def insert(self, key, value):
        self.map[key] = (value, self.epoch)

    def get(self, key):
        return self.map.get(key)
