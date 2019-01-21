def join(*args, **kwargs):
    """ Faked join method, for mocking purposes """
    return '/' + '/'.join([arg for arg in args])
