import os
import socket
import logging
import hashlib
import itertools
# noinspection PyPep8Naming
import cPickle as pickle
from collections import namedtuple

import sliding
from example.protocol import InitFile, PutData, Finalize, Request


ProtocolProxy = namedtuple("ProtocolProxy", ["send", "recv"])


class Client(object):

    CHUNK_SIZE = 10
    logger = logging.getLogger("client")

    def __init__(self, server="0.0.0.0", port=5000):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = itertools.count()
        self._server = (server, port)
        self.protocol = ProtocolProxy(self._send, self._recv)

    def send_file(self, path):
        self.logger.info("Sending %s", path)
        self.send_init(os.path.basename(path))
        with open(path, "rb") as f:
            data = f.read()
        self.send_data(data)
        self.send_finalize(data)
        self.logger.info("File sent!")

    def send_finalize(self, data):
        md5sum = hashlib.md5(data).hexdigest()
        self.send([Finalize(md5sum)])

    def send_data(self, data):
        data_len = len(data)
        last_offset = data_len - (data_len % self.CHUNK_SIZE)
        last_size = data_len - last_offset
        chunks = [(i * self.CHUNK_SIZE, self.CHUNK_SIZE)
                  for i in range(data_len / self.CHUNK_SIZE)]
        if last_size > 0:
            chunks.append((last_offset, last_size))
        chunks = [(offset, data[offset: offset + size])
                  for offset, size in chunks]
        packets = [PutData(offset, data) for offset, data in chunks]
        self.send(packets)

    def send_init(self, filename):
        packet = InitFile(filename)
        self.send([packet])

    def send(self, commands):
        self.logger.info("Initiating SlidingWindow transaction")
        sliding.SlidingWindow(self.protocol, 5, 3, 5).run(commands)

    def _send(self, command):
        request = Request(self.seq.next(), command)
        self.logger.info("Sending %s", request)
        self._socket.sendto(pickle.dumps(request), self._server)
        return request.id

    def _recv(self, timeout):
        self._socket.settimeout(timeout)
        try:
            data = self._socket.recv(1024)
        except socket.timeout:
            raise sliding.TimeoutError()
        response = pickle.loads(data)
        self.logger.info("Received %s", response)
        return response.id


if __name__ == '__main__':
    from example import config_logging
    config_logging()
    c = Client()
    c.send_file(__file__)
