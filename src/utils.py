import itertools

def has_method(instance, name):
    return hasattr(instance, name) and callable(getattr(instance, name))

def iterate_edges(i, sentinel=None):
    i_sentinels = itertools.chain((sentinel,), i, (sentinel,))
    i1, i2 = itertools.tee(i_sentinels)
    return itertools.izip(i1, itertools.islice(i2, 1, None))