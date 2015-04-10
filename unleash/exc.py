class UnleashError(Exception):
    pass


class InvocationError(UnleashError):
    pass


class ReleaseError(UnleashError):
    pass


class PluginError(UnleashError):
    pass
