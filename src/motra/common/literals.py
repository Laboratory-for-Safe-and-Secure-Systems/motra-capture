from typing import Literal


INSTALLABLE_SERVER_UNITS = Literal[
    "motra-client-mexec@.service", "motra-server.service"
]
INSTALLABLE_SERVER_UNITS = Literal[
    "motra-server-mexec@.service", "motra-client@.service"
]
INSTALLABLE_UNITS = Literal[INSTALLABLE_SERVER_UNITS, INSTALLABLE_SERVER_UNITS]

MOTRA_UNITS = Literal[
    "motra-client", "motra-client-mexec", "motra-server-mexec", "motra-server"
]
