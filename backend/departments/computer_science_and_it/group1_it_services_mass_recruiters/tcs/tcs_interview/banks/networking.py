# -*- coding: utf-8 -*-
"""TCS Technical-round Computer Networks (CN) question bank.

# SEED CONTENT: a small, hand-written STARTING set of 3 questions.
Confirmed (by direct grep across this repo, see the design review this
module came from) that NO open-ended, interview-format CN question bank
exists anywhere else in this codebase -- the OA side has a "cn" MCQ topic
(companies.py's repeated {"key": "cn", "name": "Computer Networks"}
sections), but that is a different question FORMAT (multiple-choice,
auto-graded) and is not reusable here. This file is entirely new, with no
source material to adapt from.

# TODO: needs ~7-9 more items for production use (production target:
roughly 10-12 items total, same per-tier-draw-depth and repeat-attempt-
variety ratio as every other Technical-round bank in this package -- see
oop.py's docstring for that reasoning). Topics still missing from this
seed set and worth adding first: subnetting/CIDR, DNS resolution, routing
basics (static vs dynamic), HTTP vs HTTPS/TLS handshake basics, firewalls/
NAT, and the OSI model layer-by-layer (this seed only touches TCP/IP at the
transport-layer level, OSI as a whole, and HTTP status-code basics).

Shape: {id, topic, difficulty, text, key_points} -- see banks/_kp.py.
"""
from typing import Any, Dict, List

from ._kp import kp

NETWORKING_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tcs-cn-1", "topic": "networking", "difficulty": "ninja",
        "text": "What is the main difference between TCP and UDP?",
        "key_points": [
            kp("TCP is connection-oriented and reliable (acknowledgements, retransmission, ordering)",
               "TCP guarantees delivery and correct order"),
            kp("UDP is connectionless and does not guarantee delivery or order, but has lower overhead",
               "UDP is faster/lighter but unreliable, suited to things like streaming or DNS"),
        ],
    },
    {
        "id": "tcs-cn-2", "topic": "networking", "difficulty": "digital",
        "text": "What happens, at a high level, when you type a URL into a browser and press enter -- specifically, what is DNS's role in that process?",
        "key_points": [
            kp("DNS translates the human-readable domain name into an IP address",
               "DNS resolution happens before the browser can actually connect to the server"),
            kp("describes at least one other real step in the sequence (e.g. opening a TCP connection, "
               "the TLS handshake for HTTPS, or sending the HTTP request)",
               "shows the DNS step fits into a larger connect-then-request sequence, not in isolation"),
        ],
    },
    {
        "id": "tcs-cn-3", "topic": "networking", "difficulty": "prime",
        "text": "What is the OSI model, and which layer is responsible for routing packets between different networks?",
        "key_points": [
            kp("the OSI model is a 7-layer conceptual model describing how network communication is layered "
               "(physical, data link, network, transport, session, presentation, application)",
               "names several of the seven OSI layers correctly, in roughly the right order"),
            kp("correctly identifies the Network layer (layer 3) as responsible for routing between networks",
               "connects IP addressing and routing specifically to the network layer, not the data link or transport layer"),
        ],
    },
]
