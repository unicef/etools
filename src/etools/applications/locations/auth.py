from pyrestcli.auth import BaseAuthClient
from carto.auth import _BaseUrlChecker
from carto.exceptions import CartoException


class EtoolsCartoNoAuthClient(_BaseUrlChecker, BaseAuthClient):
    """
    Simple Carto Auth class, without the API key in the request
    """
    def __init__(self, base_url):
        base_url = self.check_base_url(base_url)
        super(EtoolsCartoNoAuthClient, self).__init__(base_url)

    def send(self, relative_path, http_method, **requests_args):
        try:
            return super(EtoolsCartoNoAuthClient, self).send(
                relative_path,
                http_method.lower(),
                **requests_args
            )
        except Exception as e:
            raise CartoException(e)
