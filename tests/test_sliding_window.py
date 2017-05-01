import sliding
import helper


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
        protocol = helper.Protocol()
        for window_size in range(1, 10):
            for num_packets in range(window_size * 2):
                protocol.reset()
                packets = range(num_packets)
                sliding.SlidingWindow(protocol, window_size, 0, 0).run(packets)
                self.assertSequenceEqual(packets, protocol.responded.values())

    def test_mismatch_response(self):
        proto = MismatchProtocol()
        with self.assertRaises(sliding.UnexpectedResponse):
            sliding.SlidingWindow(proto, 1, 0, 0).run([0])
