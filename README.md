# sliding
_Protocol-agnostic, efficient sliding transmission window implementation_

## Usage
    SlidingWindow(protocol, size, max_retrans, timeout).run(packets)
    
    protocl - An object capable of sending packets and receiving responses.
    size - The window size.
    max_retrans - Max retrans attempts for each packet before failing the
        operation.
    timeout - How long to wait for a confirmation for a packet since its
        transmission.
    packets - A source of iterable data describing each packet, that `protocol`
        is capable of sending

### Theoretical Background
Many protocols dealing with transferring large amount of data, needs to do this 
in a reliable manner.

Depending on the medium the data has to travel in, this might not be a trivial 
task. data might get lost along the way, or get corrupted due to noise or other 
physical factors.

Sending the entire data in a single transmission is not very practical because 
if something goes wrong - you have to resend to whole thing again.

Thus, the data is usually split between multiple "packets", which can be 
verified, and retransmitted if needed.

To verify a packet, the receiver needs to confirm its reception.
This confirmation, is itself bound to the same conditions of the original 
packet, and might also get lost / corrupted.
The sender need to deal with these situation by issuing a re-transmission, and 
the receiver should expect duplicate packets arriving.

#### The performance issue
Waiting for confirmation on each packet before sending the next one, will
result in a bad throughput. This is because the medium will not be utilized
while waiting for the confirmation to arrive.
 
Ideally we would prefer that the sender will send the _entire_ data (split to
individual packets) to the receiver, and then wait for confirmation / rejection
on individual packets. Practically it is not always possible due to memory
limitations on both sides, and in order to avoid network congestion.

#### Sliding Window
For these reasons, protocols usually limits the number of packets allowed to be
transmitted in burst, before pausing for confirmation. 
A batch of packets that are waiting confirmation is called a _Transmission Window_

There is no need to wait for confirmation on the entire window. As confirmations
starts to arrive, more packets are can be sent, thus shifting the window
forward, or _Sliding_ it. 

### Terminology
 - **Request** - a packet sent to a receiver, that requires confirmation by the 
 receiver
 - **Retransmission Timeout** - The amount of time from the transmission of a 
 packet, in which a confirmation is expected. If no confirmation received, the 
 packet is considered lost, and should be retransmitted.
 - **Window Size** - The maximal amount of unconfirmed packets that are allowed
 to sent at any given moment.
