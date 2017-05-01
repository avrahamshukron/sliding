import abc
import time
import collections

# An object holding an information about a request currently sent and
# awaiting Ack response. Every request must be Ack'ed by the recipient in
# order for the transmission to succeed. If no confirmation received for a
# request in a given `timeout`, then the request is sent again - up to
# `max_retrans` times
Request = collections.namedtuple(
    "Request", ["end_time", "data", "retrans_left"])


class Protocol(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def send(self, data):
        """
        send a request.
        
        :param data: The data to send
        :return A unique identifier for the packet sent, that can be matched to
            a corresponding ack response.
        """

    @abc.abstractmethod
    def recv(self, timeout):
        """
        Wait for the next response, and return the Request tag it corresponds to
        
        :param timeout: How long to wait for the response in seconds.
        :raise TimeoutError: If a response is not available within `timeout`
        """


class UnexpectedResponse(Exception):
    pass


class TimeoutError(RuntimeError):
    pass


class SlidingWindow(object):

    def __init__(self, protocol, size, max_retrans, timeout, clock=time.time):
        """
        Initialize new SlidingWindow

        :param protocol: A `Protocol` implementation.
        :param size: The window size. How many packets will be sent before
            awaiting responses to arrive.
        :param max_retrans: How many times to resend a packet which hasn't
            received a response before failing the entire operation.
        :param timeout: How long (in seconds) to wait for a response for a given
            packet before initiating a retransmission. The time starts to count
            from the moment the packet is sent through the window.
        :param clock: A callable returning the current time, in seconds.
        """
        self._protocol = protocol
        self._size = size
        self._max_retrans = max_retrans
        self._timeout = timeout
        self._window = collections.OrderedDict()
        self.clock = clock

    def run(self, requests):
        """
        Execute a sliding window transmission.

        :param requests: An (`Iterator | Iterable`) of all the packets to be
            sent. Each element is passed to `protocol` when it needs to be sent. 
        """

        if not hasattr(requests, "next"):
            requests = iter(requests)
        for _ in range(self._size):
            if self._send_next(requests) is None:
                break

        while self._window:
            last_tag, packet = self._window.popitem(last=False)
            timeout = min(self._timeout, self.clock() - packet.end_time)
            try:
                tag = self._protocol.recv(timeout)
            except TimeoutError:
                if packet.retrans_left <= 0:
                    raise
                self.__send(packet.data, packet.retrans_left - 1)
                continue

            if tag != last_tag and tag not in self._window:
                raise UnexpectedResponse(tag)
            self._send_next(requests)

    def __send(self, data, retrans_left):
        tag = self._protocol.send(data)
        request = Request(end_time=self.clock() + self._timeout,
                          data=data, retrans_left=retrans_left)
        self._window[tag] = request
        return tag

    def _send_next(self, iterator):
        try:
            data = iterator.next()
        except StopIteration:
            return None
        return self.__send(data, self._max_retrans)
