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
        if timeout < 0:
            raise ValueError("timeout must be >= 0")
        if size < 1:
            raise ValueError("size must be >= 1")
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

        requests = self._iter(requests)
        self._burst(requests)

        while self._window:
            # The window is ordered by transmission time, least to most recent.
            # Each iteration we expect the response for the least recent packet
            oldest_tag, oldest_packet = next(self._window.iteritems())
            timeout = self._calculate_timeout(
                oldest_packet.end_time, self.clock())
            try:
                confirmed_tag = self._protocol.recv(timeout)
            except TimeoutError:  # Oldest packet needs to be retransmitted
                self._window.pop(oldest_tag)
                if oldest_packet.retrans_left <= 0:
                    raise
                self.__send(oldest_packet.data, oldest_packet.retrans_left - 1)
                continue

            if self._window.pop(confirmed_tag, default=None) is None:
                raise UnexpectedResponse(confirmed_tag)
            self._send_next(requests)

    def _calculate_timeout(self, end_time, now):
        """Normalize timeout to always be in [0, self._timeout]"""
        return max(0, min(self._timeout, end_time - now))

    @staticmethod
    def _iter(elements):
        if not hasattr(elements, "next"):
            elements = iter(elements)
        return elements

    def _burst(self, requests):
        for _ in range(self._size):
            if self._send_next(requests) is None:
                break

    def __send(self, data, retrans_left):
        tag = self._protocol.send(data)
        request = Request(end_time=self.clock() + self._timeout,
                          data=data, retrans_left=retrans_left)
        self._window[tag] = request
        return tag

    def _send_next(self, iterator):
        data = next(iterator, None)
        if data is not None:
            return self.__send(data, self._max_retrans)
        return None
