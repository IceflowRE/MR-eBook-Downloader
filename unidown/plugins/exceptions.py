"""
Default exceptions of plugins.
"""


class PluginException(Exception):
    """
    Base class for exceptions in a plugin.
    If catching this, it implicit that the plugin is unable to work further.

    :param msg: message
    :type msg: str

    :ivar msg: exception message
    :vartype msg: str
    """

    def __init__(self, msg=''):
        self.msg = msg
