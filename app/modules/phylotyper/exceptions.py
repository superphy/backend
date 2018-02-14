"""Custom Exception Classes for Phylotyper Module

"""


class PhylotyperError(Exception):
    """Basic exception for errors raised by Phylotyper modules"""

    def __init__(self, subtype, msg=None):
        if msg is None:
            msg = "An error occured for subtype {}".format(subtype)
        super(PhylotyperError, self).__init__(msg)
        self.subtype = subtype


class ValuesError(PhylotyperError):
    """Unknown subtype"""

    def __init__(self, subtype, msg=None):
        super(PhylotyperError, self).__init__(
            subtype, msg="Unrecognized subtype {}".format(subtype))


class DatabaseError(PhylotyperError):
    """Missing data in Database"""

    def __init__(self, subtype, data, msg=None):
        m = "Database is missing data {} for {}".format(data, subtype)
        super(PhylotyperError, self).__init__(subtype, m)
        self.data = data
