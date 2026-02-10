import http


class UdpuException(Exception):
    """Base exception of udpu service"""


class APIException(UdpuException):
    """The main error of FCC REST API. The mail goal of this class is define
    a general structure of errors, which will be automatically converted into
    appropriate and correct HTTP responses."""

    status: http.HTTPStatus = None

    def __init__(self, code: int = None, title: str = None, detail: str = None, source: str = None):
        super().__init__()

        self.title = title
        self.code = code
        self.detail = detail
        self.source = source

    @property
    def code(self):
        return self.__code

    @code.setter
    def code(self, value):
        self.__code = value
        if self.__code is None and self.status is not None:
            # Let's try get code from a status
            self.__code = self.status.value

    @property
    def title(self):
        return self.__title

    @title.setter
    def title(self, value):
        self.__title = value
        if self.__title is None and self.status is not None:
            # Let's try get title from a status
            self.__title = self.status.phrase

    @property
    def detail(self):
        return self.__detail

    @detail.setter
    def detail(self, value):
        self.__detail = value
        if self.__detail is None and self.status is not None:
            # Let's try get detail from a status
            self.__detail = self.status.description

    @property
    def source(self):
        return self.__source

    @source.setter
    def source(self, value):
        self.__source = value

    def to_dict(self):
        """Returns dictionary with error message"""
        _dict = {"code": self.code, "title": self.title}

        if self.source is not None:
            _dict.update({"source": self.source})

        if self.detail is not None:
            _dict.update({"detail": self.detail})

        return _dict


class InternalServerError(APIException):
    """Internal server API error. If this error raised, a response with appropriate HTTP will be sent to the client."""

    status = http.HTTPStatus.INTERNAL_SERVER_ERROR


class BadRequestError(APIException):
    """Bad request API error. If this error raised, a response with appropriate HTTP will be sent to the client."""

    status = http.HTTPStatus.BAD_REQUEST


class RecordNotFound(APIException):
    """Not Found API error. If this error raised, a response with appropriate HTTP will be sent to the client."""

    status = http.HTTPStatus.NOT_FOUND


class RecordAlreadyExists(BadRequestError):
    """Record already exists"""
