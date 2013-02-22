============================================================
Why Distributed Transactions Suck
============================================================

The relative speed of operations::

                     Cycles      Seconds       Scaled
    -------------------------------------------------
    CPU Register        1        0.33 ns         1 s
    L1 cache            3        1 ns            3 s
    L2 cache           14        4.7 ns         14 s
    RAM               250        83 ns         4.2 m
    Network         6 mil        2 ms        69 days
    Disk Write    7.8 mil        2.6 ms      90 days
    Disk Read      15 mil        5 ms       173 days

------------------------------------------------------------
Write Ahead Logging
------------------------------------------------------------

Write ahead logging can be used to write transaction
details as they occur. If the transaction fails because
of failure, when the DB comes back up, it will look for
commit messages. If they are found, the transaction is
recovered, else they are dropped::

    TxnA start  -> TxnA change -> TxnB start -> TxnC commit
    TxnA commit -> TxnB change -> TxnB commit

This is optimized for writing and thus is bad for queries.
So all the transactions need to be in RAM and the transactions
must be committed ASAP.  Also, if the log fills up, then
everyone is blocked.

------------------------------------------------------------
Two Phase Commit
------------------------------------------------------------

Distributed Transaction Minimums::

    Wt = 2 + 2D
    Mt = 4D

    D = databases
    W = writes
    M = messages

------------------------------------------------------------
Why They Suck
------------------------------------------------------------

In any distributed system, messaging will fail. The only way
to ensure operations are done is to retry them, so every
operation must be tried multiple times:

* Inefficient use of database resources
* Scaling of the transaction coordinator
* Availability is the intersection of all systems involved
* Idempotent operations don't need distributed transactions

Examples of idempotent examples:

* non-mutating read: don't make any changes
* assignment or replacement: aaaabbbb
* order safe: ababaabb

To make operations idempotent, the following must be done:

* Assign every operation an ID
* Define a DAG for every possible state
* Track what the operations affect
* Define compensation policies
* Define rules for how different operations can combine

This no longer needs distributed transactions and can be
performed across databases. Customers must now know that
transfers may be in process.

------------------------------------------------------------
Techniques
------------------------------------------------------------

Explicit Transactions handle all the requirements in the
application

Optimistic Locking works as follows:

* Keep a current revision number
* increment revision number on update
* require revision number with every update
* if number passed in is not current value, reject
* parallel operations are disallowed

Immutable Versions works as follows:

* Need two systems: base and detail
* detail depends on base data
* base data needs to change
* best if base is read before detail

Herd workflow engine

============================================================
POA Gems
============================================================

------------------------------------------------------------
Endemic Spreading
------------------------------------------------------------

Choose a network peer at random and exchange data with each
other via push/pull gossip udp messages::

    a -> status -> b
    b -> status -> a
    # continue until consensus is statistically correct

------------------------------------------------------------
CAP
------------------------------------------------------------

Given consistency, availability, and partition tolerance:

* **CA**: single site database, database clusters
* **CP**: majority protocols, distributed locking and
  databases if you are on the wrong side of the partition
  you cannot make progress, otherwise you are good to go.
* **PA**: caching, dns, dynamo

------------------------------------------------------------
Scalable Architecture
------------------------------------------------------------

* Partition your use cases (users, batch/live, etc) so that problems in
  one will not break the other
* Plan for the worst case, but have your system run at the common case (elastic)
* Fail fast and restart instead of browning out
* Logging does not scale (IO starts to be a killer)
* Dig into unusual outages as there may be more there that meets the eye.

============================================================
Load Balances Don't Have To Suck
============================================================

------------------------------------------------------------
OSI 7-Layer Model:
------------------------------------------------------------

* (7) Application
* (6) Presentation
* (5) Session
* (4) Transport (TCP/IP)
* (3) Network
* (2) Data Link
* (1) Physical

The load balancer for HTTP operates at layer 7, and the
servers can be balanced by being pointed to with a VIP.
The load balancer can do a number of things to help
backend services:

* header injection (X-Forward)
* SSL processing

The load balancer for services operates at layer 4 and
has no knowledge about the content of the request/service.
This will forward SSL processing to the backend service
and can increase performance of the load balancer.

------------------------------------------------------------
Common load balancing policies:
------------------------------------------------------------

* Round Robin

  This take turns between different servers.
  This doesn't take into account the variations in request
  type such as get current time vs encode an entire movie
  (i.e. server load). 

* Random

  This just chooses the next server at random.
  This has no way to prevent hot spots, we can choose
  the same host every time or more often than the others.

* Max Connections

  This associates the next request with any server that
  has and number of connections left (defined max connections
  for worst case).
  This has the same problem as Round Robin.

* Least Connections

  This associates the next request with the server with
  the least available connections to it.
  This has no way to prevent routing requests to a broken
  server.

------------------------------------------------------------
Policies for Managing overloaded load balancers:
------------------------------------------------------------

* Surge Connection Queue

  If any max connection load balancer is full, then the
  connections are queued and delivered when there is an
  open connection (connections may be dropped by client
  but work is still done; don't use).

* Spillover

  If the request cannot be assigned, just return an error
  and let the client try again.

------------------------------------------------------------
How can we make a better load balancer (JLB):
------------------------------------------------------------

* Distributed load balancer
* Scales to infinity (horizontal)
* Better fault tolerance
* Simple load balancing strategy
* Cheap hardware
* Open software that we can maintain

                     /=> Switch (Juniper iEX4500)
    Cisco 3750-e => JLB-E
                     \=> Router (Quanta SW)

* Equal Cost Multi-Path (ECMP)

  Takes in large quantaties of data to a VIP and basically
  uses consistent hashing to distribute load across the
  hosts behind it.

* Intel DPDK
* Yet Another Network Node (YANN)

  Internal kernel module that accepts Ncap/Dcap packets
  and reinterprets them as the initial packets. It detects
  overload and accepts configuration.

------------------------------------------------------------
The JLB Process
------------------------------------------------------------

1. Ingress packets arrive at ingress server that wraps packet
2. It sends the fake packet to a primary flow tracker
3. This forwards it to a secondary flow tracker
4. This is fowarded to the web server
5. The web server YANN decodes the packet and sends it back up the chain
6. Once back to ingress, ingress can forward all queued data directly
   to the web server.
7. Web server sends fake packets to egress server to flow the data out.

a. On failure, the new ingress server contacts the primary flow tracker
   and gets current state (if it exists) or starts the process again.
b. All SSL happens on the host machine
c. The ingress server is chosen by consistent hashing
d. The YANN knows its own state, and on close publishes updates to the 
   flow servers.

In the YANN module IRQ handler, we can quickly check if we can handle
the packet or not (CPU utilization, message queue, etc), and if not,
it sends a reject message back through the flow trackers which choose
another host to route to:

* A TTL is added to the message so that it isn't rejected forever

============================================================
Amazon Web Services
============================================================

------------------------------------------------------------
S3
------------------------------------------------------------

In order to allow S3 to evenly shard your data, try not to
use keys of the form `<database>/<date>/<name>` as you will
eventually hit a scaling load (when a lot of keys hash to the
same bucket). Instead, you can do something like::

    key = "#{database}/#{date.now}/#{name}"
    key = hash(key) + "/" + key

Which will allow your keys to be evenly distributed throughout
S3 for as long as you are using it.

============================================================
Quorums and Chains: Consensus Beyond Paxos
============================================================

------------------------------------------------------------
Summary
------------------------------------------------------------

What if the central storage fails (durability)::

    client -> writer(n) -> storage
    client -> reader(n) -> storage

We can add a copy or backup of the data on every committ;
what if we get too much load to continue this (availability)::

    client -> writer -> storage -> backup
    client -> writer -> xxxxxxx -> backup
                     -> storage <- backup
    client -> writer -> storage -> backup

We can add a hot stand by, but what if those get out of sync
or are partitioned::

    client -> writer -> storage -|
    client -> reader -> storage -|

------------------------------------------------------------
Chain Architecture
------------------------------------------------------------

Nodes chain off of each other and effectively serialize the
events.

------------------------------------------------------------
Quorum
------------------------------------------------------------

On write, the writer must contact a majority of the storage
nodes, if it does, it is granted a write quorum and is
allowed to write. The same is true for a reader.

With (3) storage nodes, the reader and writer need 2 nodes
for quorum and thus there will be node intersection between
the two events.

To handle which version of the data is correct, simply use
timestamps to retrieve the latest version of the data. And
for writers, the latest time writer gets the ability to
write. Problems:

* out of sync clocks
* bad timestamps
* what is the specification (what does "works" mean)

Can do a two phase write where we get the current highest
write version and then make ours higher (so the order is
preserved).

------------------------------------------------------------
Atomic Register Specification
------------------------------------------------------------

The best way to determine if a distributed system works is
to create a model and:

* establish if it works (correctness)
* establish when it works (liveness)
* establish theoretical peformance

There exists one such partial order such that each read
operation sees the last write operation:

* The operations are serializable (isolated)
* A_e -> B_s <=> A -> B (operations are partially ordered)
* (A -> B) ^ ~(B -> A) <=> A || B (concurrent operations)

Then look at the possible states as a graph (acyclic if
possible) then determine:

* can take a step from every state (liveness)
* no infinite traces (termination)
* every trace is correct (correctness; automate with TLA+)

Problems with atomic registers (dynamo doesn't use them):

* no atomic test and set
* write does not return the previous value
* no way to lock

------------------------------------------------------------
Asyncronous Message Passing
------------------------------------------------------------

Given a collection of processes that can receive messages:

1. select a message
2. deliver the mssage
3. update the process state machine with message
4. process can send new messages

a. process may fail and no longer receive messages
b. null messages are ok (to change state of machine)
c. can deliver in a finite number of steps (messages are not dropped)

This model is completely deterministic given the order of
message delivery, failure detection is impossible, and
the messaging is asynchronous meaning it cannot handle timeouts.

To reason about the system, define the state machiens for
the processes and apply the model::

    Reader Process
    ---------------------------------------------------
    state    message     new state           messages
    ---------------------------------------------------
    any      write       if T > t, update    ack
    any      read        no change           time,value

    Writer Process
    ---------------------------------------------------
    state    message     new state           messages
    ---------------------------------------------------
    init     write(x)    reading             read
    reading  time,value  if Q, writing       write(T, x)
    writing  ack         if Q, done          reply

    T = new time (higher time)
    t = existing time
    Q = quorum

------------------------------------------------------------
ABD Algorithm
------------------------------------------------------------

Here is how a writer works in the ABD algorithm:

1. Client puts a message in buffer requesting a write
2. Writer pulls a message from the buffer and processes it
3. The writer sends a number of read messages to get a quorum
4. Any storage node gets a read message and sends a message with
   the read value.
5. Once the writer gets its quorum, it sends the write messages
   to the buffer.
6. The write message gets delivered to a storage node (all of
   them in time). And They each return an ack message to the
   buffer.
7. The writer gets back its quorum of acks and then sends a
   response back to the client.

------------------------------------------------------------
Consensus
------------------------------------------------------------

Powered by Replicated State Machines:

* A write once abstraction
* proposers all attempt to write values, only one succeeds
* readers get the recent value or none at all
* required properties: valid, correct

This can easily be created with a chain replication:

* just ignore all but the first write
* allows pipelining (writes can quickly flow without blocking)
* but not fault tolerant

------------------------------------------------------------
Paxos Consensus
------------------------------------------------------------

* Quorum based algorithm
* proposer is two rounds and does not always succeed (not
  guranteed to terminate), FLP Impossibility Proof
* storage nodes host the state machine
* Chubby, alf, zookeeper
* no pipelining (batching and windowing)
* requires redrives in the event of contention

------------------------------------------------------------
Dynamic Configuartion
------------------------------------------------------------

* each node in the chain has an active config prefix (not all)
* can create a dynamic chain architecture
* swami decides on join and leave events
* chain nodes upgrade at their own pace
* no reconfiguration event