import logging
import unittest
import itertools

import collections

import sliding


Request = collections.namedtuple("Request", ("id", "data"))


class Protocol(sliding.Protocol):

    _logger = logging.getLogger("sliding.tests.protocol")

    def __init__(self):
        self.request_seq = itertools.count()
        self.reset()

    def reset(self):
        # All packets received through `send`
        self.request_sent = collections.OrderedDict()
        # Packets awaiting response
        self.awaiting_response = collections.OrderedDict()
        # Packets responded through `recv`
        self.responded = collections.OrderedDict()

    def send(self, data):
        request_id = self.request_seq.next()
        self.request_sent[request_id] = data
        self.awaiting_response[request_id] = data
        self._logger.info("sending Request(id=%s, data=%s)", request_id, data)
        return request_id

    def should_drop(self, req_id, data):
        return False

    def recv(self, timeout):
        data, req_id = self._recv()
        if self.should_drop(req_id, data):
            self._logger.info(
                "dropping response for Request(id=%s, data=%s", req_id, data)
            raise sliding.TimeoutError()
        self._logger.info("returning Response(id=%s)", req_id)
        self.responded[req_id] = data
        return req_id

    def _recv(self):
        return self.awaiting_response.popitem(last=False)


class TestCase(unittest.TestCase):

    def setUp(self):
        super(TestCase, self).setUp()
        fmt = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
        formatter = logging.Formatter(fmt)

        file_handler = logging.FileHandler(
            "output/{}.log".format(type(self).__name__), "w")
        file_handler.setFormatter(formatter)
        logging.root.addHandler(file_handler)
        logging.root.setLevel(logging.DEBUG)
