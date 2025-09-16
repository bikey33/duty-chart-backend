# users/authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

class AccessTokenOnlyAuthentication(JWTAuthentication):
    """
    Custom auth class that only accepts valid ACCESS tokens.
    Refresh tokens or any other type will be rejected.
    """
    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if token.payload.get('token_type') != 'access':
            raise InvalidToken('Only access tokens are allowed for this endpoint')
        return token
