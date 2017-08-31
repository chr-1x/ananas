import mastodon, requests, threading
from contextlib import closing

def __stream(self, endpoint, listener, params = {}, async=False):
    """
    Internal streaming API helper.

    Returns a handle to the open connection that the user can close if they
    wish to terminate it.
    """

    headers = {}
    if self.access_token != None:
        headers = {'Authorization': 'Bearer ' + self.access_token}
    url = self.api_base_url + endpoint

    connection = requests.get(url, headers = headers, data = params, stream = True)

    class __stream_handle():
        def __init__(self, connection):
            self.connection = connection

        def close(self):
            self.connection.close()

        def _threadproc(self):
            with closing(connection) as r:
                try:
                    listener.handle_stream(r.iter_lines())
                except AttributeError as e:
                    # Eat AttributeError from requests if user closes early
                    pass
            return 0

    handle = __stream_handle(connection)

    if async:
        t = threading.Thread(args=(), target=handle._threadproc)
        t.start()
        return handle
    else:
        # Blocking, never returns (can only leave via exception)
        with closing(connection) as r:
            listener.handle_stream(r.iter_lines())
###
# Streaming
###
def user_stream(self, listener, async=False):
    """
    Streams events that are relevant to the authorized user, i.e. home
    timeline and notifications. 'listener' should be a subclass of
    StreamListener which will receive callbacks for incoming events.

    If async is False, this method blocks forever.

    If async is True, 'listener' will listen on another thread and this method 
    will return a handle corresponding to the open connection. The
    connection may be closed at any time by calling its close() method.
    """
    return __stream(self, '/api/v1/streaming/user', listener, async=async)

def public_stream(self, listener, async=False):
    """
    Streams public events. 'listener' should be a subclass of StreamListener
    which will receive callbacks for incoming events.

    If async is False, this method blocks forever.

    If async is True, 'listener' will listen on another thread and this method 
    will return a handle corresponding to the open connection. The
    connection may be closed at any time by calling its close() method.
    """
    return __stream(self, '/api/v1/streaming/public', listener, async=async)

def local_stream(self, listener, async=False):
    """
    Streams local events. 'listener' should be a subclass of StreamListener
    which will receive callbacks for incoming events.

    If async is False, this method blocks forever.

    If async is True, 'listener' will listen on another thread and this method 
    will return a handle corresponding to the open connection. The
    connection may be closed at any time by calling its close() method.
    """
    return __stream(self, '/api/v1/streaming/public/local', listener, async=async)

def hashtag_stream(self, tag, listener, async=False):
    """
    Returns all public statuses for the hashtag 'tag'. 'listener' should be
    a subclass of StreamListener which will receive callbacks for incoming
    events.

    If async is False, this method blocks forever.

    If async is True, 'listener' will listen on another thread and this method 
    will return a handle corresponding to the open connection. The
    connection may be closed at any time by calling its close() method.
    """
    return __stream(self, '/api/v1/streaming/hashtag', listener, params={'tag': tag}, async=async)

mastodon.Mastodon.user_stream = user_stream
mastodon.Mastodon.public_stream = public_stream
mastodon.Mastodon.local_stream = local_stream
mastodon.Mastodon.hashtag_stream = hashtag_stream
mastodon.Mastodon._patched = True
