import hashlib
import logging
import os
import socket
import cPickle as pickle
import tempfile

import time

import shutil

from example.protocol import InitFile, PutData, Finalize, Ack


class Server(object):

    logger = logging.getLogger("server")

    def __init__(self, port=5000, server_dir=None, delay=0.0):
        self._port = port
        self._delay = delay
        self._dir = (server_dir if server_dir is not None
                     else os.path.join(os.path.dirname(__file__), "serve"))
        if not os.path.isdir(self._dir):
            os.makedirs(self._dir)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("0.0.0.0", self._port))
        self.handlers = {
            InitFile: self._init_file,
            PutData: self._put_data,
            Finalize: self._finalize
        }
        self.fobj = None

    def run(self):
        self.logger.info("Server started running")
        while True:
            data, addr = self._sock.recvfrom(1024)
            self.logger.debug("Received message from %s", addr)
            response = self.handle(data)
            self._sock.sendto(response, addr)

    def handle(self, data):
        request = pickle.loads(data)
        return pickle.dumps(self._handle(request))

    def _handle(self, request):
        self.logger.debug("Received %s", request)
        handler = self.handlers[type(request.command)]
        handler(request.command)
        ack = Ack(request.id)
        time.sleep(self._delay)
        self.logger.debug("Sending %s", ack)
        return ack

    def _init_file(self, command):
        self.logger.info("File transfer initiated: %s", command.filename)
        self._filename = command.filename
        self.fobj = tempfile.NamedTemporaryFile(
            suffix=command.filename, dir=self._dir, delete=False)

    def _put_data(self, command):
        self.fobj.seek(command.offset)
        self.fobj.write(command.data)

    def _finalize(self, command):
        self.fobj.seek(0)
        data = self.fobj.read()
        md5sum = hashlib.md5(data).hexdigest()
        if md5sum != command.md5:
            raise ValueError("MD5 checskum failed. Expected %s, Computed %s" %
                             (command.md5sum, md5sum))
        self.fobj.close()
        shutil.move(self.fobj.name, os.path.join(self._dir, self._filename))
        self.logger.info("File received successfully: %s", self._filename)
        self.fobj = None
        self._filename = None


if __name__ == '__main__':
    from example import config_logging
    config_logging()
    s = Server(delay=0.1)
    s.run()
