from django.conf import settings
from django.utils.translation import gettext_lazy as _

import jwt
from jwt import InvalidAlgorithmError, InvalidTokenError
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenBackendError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken


class LeewayTokenBackend(TokenBackend):
    def __init__(
            self,
            algorithm,
            signing_key=None,
            verifying_key=None,
            audience=None,
            issuer=None,
            leeway=0,
    ):
        super().__init__(algorithm, signing_key, verifying_key, audience, issuer)
        self.leeway = leeway

    def decode(self, token, verify=True):
        """
        Performs a validation of the given token and returns its payload
        dictionary.

        Raises a `TokenBackendError` if the token is malformed, if its
        signature check fails, or if its 'exp' claim indicates it has expired.
        """
        try:
            return jwt.decode(
                token, self.verifying_key, algorithms=[self.algorithm], verify=verify,
                audience=self.audience, issuer=self.issuer, leeway=self.leeway,
                options={'verify_aud': self.audience is not None, "verify_signature": verify}
            )
        except InvalidAlgorithmError as ex:
            raise TokenBackendError(_('Invalid algorithm specified')) from ex
        except InvalidTokenError:
            raise TokenBackendError(_('Token is invalid or expired'))


class LeewayAccessToken(AccessToken):

    def get_token_backend(self):
        return LeewayTokenBackend(
            api_settings.ALGORITHM,
            api_settings.SIGNING_KEY,
            api_settings.VERIFYING_KEY,
            api_settings.AUDIENCE,
            api_settings.ISSUER,
            settings.LEEWAY
        )
