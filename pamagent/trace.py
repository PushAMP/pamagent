from collections import namedtuple


TraceNode = namedtuple('TraceNode',
                       ['start_time', 'end_time', 'name', 'params', 'children', 'label'])

RootNode = namedtuple('RootNode',
                      ['start_time', 'empty0', 'empty1', 'root', 'attributes'])


def node_start_time(root, node):
    return int((node.start_time - root.start_time) * 1000.0)


def node_end_time(root, node):
    return int((node.end_time - root.start_time) * 1000.0)


def root_start_time(root):
    return root.start_time / 1000.0
