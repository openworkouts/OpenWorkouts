
def join(*args, **kwargs):
    """
    Faked join method, for mocking purposes
    """
    return '/' + '/'.join([arg.strip('/') for arg in args])
