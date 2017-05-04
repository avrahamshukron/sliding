from collections import namedtuple

InitFile = namedtuple("InitFile", ["filename"])
PutData = namedtuple("PutData", ["offset", "data"])
Finalize = namedtuple("Finalize", ["md5"])

Request = namedtuple("Request", ["id", "command"])
Ack = namedtuple("Ack", "id")
