from typing import List, Union

from drf_spectacular.extensions import OpenApiAuthenticationExtension, _SchemaType


class CookieJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = "authapp.authentication.CookieJWTAuthentication"
    name = "CookieJWT"

    def get_security_definition(
        self, auto_schema
    ) -> Union[_SchemaType, List[_SchemaType]]:
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "access_token",
            "description": "Authentication via HttpOnly cookie.",
        }
