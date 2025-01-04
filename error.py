from flask import render_template

ERROR_MESSAGES = {
    # Client error responses (400–499)
    400: {"short": "Bad Request", "long": "The request could not be understood by the server due to malformed syntax. Please correct the request and try again."},
    401: {"short": "Unauthorized", "long": "You must authenticate to access this resource. Please log in with the correct credentials."},
    402: {"short": "Payment Required", "long": "Payment is required to access this resource. Please complete the payment process."},
    403: {"short": "Forbidden", "long": "You are not authorized to access this resource. Contact the administrator if you believe this is a mistake."},
    404: {"short": "Not Found", "long": "The page you are looking for doesn’t exist. Check the URL and try again."},
    405: {"short": "Method Not Allowed", "long": "The HTTP method used is not allowed for this resource. Please refer to the API documentation."},
    406: {"short": "Not Acceptable", "long": "The server cannot produce a response matching the acceptable criteria set in the request."},
    407: {"short": "Proxy Authentication Required", "long": "You must authenticate with a valid proxy to access this resource."},
    408: {"short": "Request Timeout", "long": "The server timed out waiting for the request. Please try again later."},
    409: {"short": "Conflict", "long": "The request could not be completed due to a conflict with the current state of the resource."},
    410: {"short": "Gone", "long": "The requested resource is no longer available on the server and has been permanently removed."},
    411: {"short": "Length Required", "long": "The request does not specify the length of its content, which is required by the server."},
    412: {"short": "Precondition Failed", "long": "The server does not meet one of the preconditions specified in the request."},
    413: {"short": "Payload Too Large", "long": "The request payload is too large for the server to process."},
    414: {"short": "URI Too Long", "long": "The requested URI is too long for the server to process."},
    415: {"short": "Unsupported Media Type", "long": "The server does not support the media type transmitted in the request."},
    416: {"short": "Range Not Satisfiable", "long": "The requested range is not satisfiable by the server."},
    417: {"short": "Expectation Failed", "long": "The server could not meet the expectation given in the request's Expect header."},
    418: {"short": "I'm a teapot", "long": "I'm a teapot. This server is a teapot, not a coffee machine."},
    421: {"short": "Misdirected Request", "long": "The request was directed at a server that is not able to produce a response."},
    422: {"short": "Unprocessable Entity", "long": "The request was well-formed but could not be processed due to semantic errors."},
    423: {"short": "Locked", "long": "The resource that is being accessed is locked."},
    424: {"short": "Failed Dependency", "long": "The request failed because it depended on another request that failed."},
    425: {"short": "Too Early", "long": "The server is unwilling to process the request because it might be replayed."},
    426: {"short": "Upgrade Required", "long": "The client should switch to a different protocol as indicated by the server."},
    428: {"short": "Precondition Required", "long": "The server requires the request to be conditional to avoid conflicts."},
    429: {"short": "Too Many Requests", "long": "You have made too many requests in a short period. Please wait and try again later."},
    431: {"short": "Request Header Fields Too Large", "long": "The server cannot process the request because its header fields are too large."},
    451: {"short": "Unavailable For Legal Reasons", "long": "The requested resource is unavailable for legal reasons."},

    # Server error responses (500–599)
    500: {"short": "Internal Server Error", "long": "The server encountered an unexpected condition and could not complete your request. Please try again later."},
    501: {"short": "Not Implemented", "long": "The server does not support the functionality required to fulfill the request."},
    502: {"short": "Bad Gateway", "long": "The server received an invalid response from an upstream server."},
    503: {"short": "Service Unavailable", "long": "The service is temporarily unavailable due to maintenance or overload. Please try again later."},
    504: {"short": "Gateway Timeout", "long": "The server did not receive a timely response from an upstream server."},
    505: {"short": "HTTP Version Not Supported", "long": "The HTTP protocol version used in the request is not supported by the server. Please use a compatible version."},
    506: {"short": "Variant Also Negotiates", "long": "The server encountered an internal configuration error while negotiating the content."},
    507: {"short": "Insufficient Storage", "long": "The server does not have enough storage to complete the request."},
    508: {"short": "Loop Detected", "long": "The server detected an infinite loop while processing the request."},
    510: {"short": "Not Extended", "long": "The server requires further extensions to fulfill the request."},
    511: {"short": "Network Authentication Required", "long": "The client must authenticate to gain network access."}
}

def handle_error(e):
    error_code = e.code if hasattr(e, 'code') else 500 
    error = ERROR_MESSAGES.get(error_code, {"short": "Error", "long": "An unexpected error occurred."})
    return render_template('error.html', error=error_code, short_message=error["short"], long_message=error["long"]), error_code
