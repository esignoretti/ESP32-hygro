class RingBuffer:
    def __init__(self, capacity):
        self._buf = [None] * capacity
        self._cap = capacity
        self._head = 0
        self._full = False

    def append(self, temp, humidity):
        self._buf[self._head] = (temp, humidity)
        self._head = (self._head + 1) % self._cap
        if self._head == 0:
            self._full = True

    def __len__(self):
        return self._cap if self._full else self._head

    def __getitem__(self, idx):
        if idx < 0 or idx >= len(self):
            raise IndexError
        if self._full:
            idx = (self._head + idx) % self._cap
        return self._buf[idx]

    def as_list(self):
        n = len(self)
        if n == 0:
            return []
        if self._full:
            return self._buf[self._head:] + self._buf[:self._head]
        return self._buf[:n]
