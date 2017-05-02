import helper
import sliding


class TestClock(object):
    """
    Simulates a clock for testing purposes
    """
    def __init__(self, sequence):
        self.seq = iter(sequence)

    def __call__(self):
        return self.seq.next()


class TimeoutProtocol(helper.Protocol):
    """
    Protocol that always times out on `recv`
    """
    def recv(self, timeout):
        raise sliding.TimeoutError()


class MismatchProtocol(helper.Protocol):
    """
    Protocol that always returns a mismatching response
    """
    def recv(self, timeout):
        return self.request_seq.next()


class ReverseProtocol(helper.Protocol):
    """
    Protocol that always sends response for the most _recent_ request
    """
    def _recv(self):
        return self.awaiting_response.popitem(last=True)


class TimeoutRecorderProtocol(helper.Protocol):
    """
    Protocol that verifies timeout values passed to `recv`
    """
    def __init__(self):
        super(TimeoutRecorderProtocol, self).__init__()
        self.timeouts = []

    def recv(self, timeout):
        self.timeouts.append(timeout)
        return super(TimeoutRecorderProtocol, self).recv(timeout)


class TestSlidingWindow(helper.TestCase):

    longMessage = True

    def test_window_size(self):
        """
        Test that without any response being received, at most `window_size` 
        packets are sent, depending on how many packets were actually queued.
        """
        max_packets = 100
        window_size = max_packets / 2
        protocol = TimeoutProtocol()
        for num_packets in xrange(1, max_packets):
            protocol.reset()
            requests = range(num_packets)
            expected = range(min(num_packets, window_size))
            with self.assertRaises(sliding.TimeoutError):
                sliding.SlidingWindow(protocol, window_size, 0, 0).run(requests)
            self.assertSequenceEqual(
                protocol.awaiting_response.values(), expected)

    def test_max_retrans(self):
        """
        Test that when timed out, each packet is sent again `max_retrans` 
        times before operation fails, and that retransmissions are done in 
        the same order the packets were sent 
        """
        protocol = TimeoutProtocol()
        for num_packets in range(1, 10):
            packets = range(num_packets)
            for max_retrans in range(10):
                protocol.reset()
                with self.assertRaises(sliding.TimeoutError):
                    sliding.SlidingWindow(
                        protocol, num_packets, max_retrans, 0).run(packets)
                # +1 because each packet is sent at least once, even when
                # max_retrans = 0.
                expected = packets * (max_retrans + 1)
                self.assertSequenceEqual(
                    expected, protocol.request_sent.values(),
                    msg="num_packets = %s, max_retrans = %s" %
                        (num_packets, max_retrans))

    def test_window_advancement(self):
        """
        Test normal window advancements, where we send 2 times more packets 
        than `windows_size`, thus ensuring full window offset 
        """
        for window_size in range(1, 10):
            for num_packets in range(window_size * 2):
                protocol = helper.Protocol()
                packets = range(num_packets)
                sliding.SlidingWindow(protocol, window_size, 0, 0).run(packets)
                self.assertSequenceEqual(packets, protocol.responded.values())

    def test_mismatch_response(self):
        """
        Test that a response to a packet never sent triggers UnexpectedResponse
        """
        proto = MismatchProtocol()
        with self.assertRaises(sliding.UnexpectedResponse):
            sliding.SlidingWindow(proto, 1, 0, 0).run([0])

    def test_out_of_order_response(self):
        max_packets = 10
        for num_packets in xrange(1, max_packets):
            for window_size in range(1, num_packets):
                protocol = ReverseProtocol()
                packets = range(num_packets)
                sliding.SlidingWindow(protocol, window_size, 0, 0).run(packets)


class TimeTravelTest(helper.TestCase):

    def test_recv_negative_timeout(self):
        """
        Test that if more than `timeout` time passed since a packet 
        transmission, the timeout value passed to `recv` will be 0
        """
        _timeout = 5
        expected_timeouts = [0]
        protocol = TimeoutRecorderProtocol()
        sliding.SlidingWindow(
            protocol, 1, 0, _timeout, TestClock([0, _timeout + 1])).run([0])
        self.assertSequenceEqual(expected_timeouts, protocol.timeouts)

    def test_clock_backward_timeout(self):
        """
        Test that if the time is set back between transmission and `recv`,
        the timeout value sent to `recv` is limited by the `timeout` param of
        the window
        """
        timeout = 5
        protocol = TimeoutRecorderProtocol()
        sliding.SlidingWindow(
            protocol, 1, 0, timeout, TestClock([10, 5])).run([0])
        self.assertSequenceEqual(protocol.timeouts, [timeout])


class TestInitialization(helper.TestCase):
    def test_init_negative_timeout(self):
        """
        Test validation on `timeout` value passed to `SlidingWindow` which must 
        be at least 0.
        """
        with self.assertRaises(ValueError):
            sliding.SlidingWindow(None, 1, 0, -1)

    def test_init_size(self):
        """
        Test validation on `size` value passed to `SlidingWindow`, which must 
        be at least 1.
        """
        for value in [-1, 0]:
            with self.assertRaises(ValueError):
                sliding.SlidingWindow(None, value, 0, 1)

