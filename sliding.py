import abc
import collections


Request = collections.namedtuple("Request", ["data", "retrans_left"])


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


def run_sliding_window(requests, protocol, size, max_retrans, timeout):
    """
    Execute a sliding window transmission.
     
    :param requests: An Iterator | Iterable of all the packets to be sent.
        Each element is passed to `protocol` when it needs to be sent. 
    :param size: The window size. How many packets will be sent before awaiting 
        responses to arrive
    :param max_retrans: How many times to resend a packet which hasn't received
        a response before failing the entire operation 
    :param timeout: How long (in seconds) to wait for a response before 
        initiating a retransmission
    :param protocol: A `Protocol` implementation.
    """
    window = collections.OrderedDict()
    if not hasattr(requests, "next"):
        requests = iter(requests)
    for _ in range(size):
        if _send_next(requests, window, max_retrans, protocol) is None:
            break

    while window:
        try:
            tag = protocol.recv(timeout)
        except TimeoutError:
            _, packet = window.popitem(last=False)
            if not packet.retrans_left:
                raise
            __send(packet.data, window, packet.retrans_left - 1, protocol)
            continue

        if tag not in window:
            raise UnexpectedResponse(tag)
        window.pop(tag)
        _send_next(requests, window, max_retrans, protocol)


def __send(data, window, retrans_left, protocol):
    tag = protocol.send(data)
    window[tag] = Request(data, retrans_left)
    return tag


def _send_next(iterator, window, max_retrans, protocol):
    try:
        return __send(
            iterator.next(), window, max_retrans, protocol)
    except StopIteration:
        return None
