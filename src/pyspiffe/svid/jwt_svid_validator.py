"""
This module manages the validations of JWT tokens.
"""

import datetime
from typing import List, Set, Dict, Any
from calendar import timegm

from pyspiffe.svid import INVALID_INPUT_ERROR

from pyspiffe.svid.exceptions import (
    TokenExpiredError,
    InvalidClaimError,
    InvalidAlgorithmError,
    InvalidTypeError,
    MissingClaimError,
)

AUDIENCE_NOT_MATCH_ERROR = 'audience does not match expected value'
"""str: audience does not match error message."""


class JwtSvidValidator(object):
    """Performs validations on a given token checking compliance to SPIFFE specification.
    See `SPIFFE JWT-SVID standard <https://github.com/spiffe/spiffe/blob/master/standards/JWT-SVID.md>`

    """

    _REQUIRED_CLAIMS = ['aud', 'exp', 'sub']
    _SUPPORTED_ALGORITHMS = [
        'RS256',
        'RS384',
        'RS512',
        'ES256',
        'ES384',
        'ES512',
        'PS256',
        'PS384',
        'PS512',
    ]

    _SUPPORTED_TYPES = ['JWT', 'JOSE']

    def __init__(self) -> None:
        pass

    def validate_headers(self, headers: Dict[str, str]) -> None:
        """Validates token headers by verifying if headers specifies supported algorithms and token type.

        Type is optional but in case it is present, it must be set to one of the supported values (JWT or JOSE).

        Args:
            headers: Token headers.

        Returns:
            None.

        Raises:
            ValueError: In case header is not specified.
            InvalidAlgorithmError: In case specified 'alg' is not supported as specified by the SPIFFE standard.
            InvalidTypeError: In case 'typ' is present in header but is not set to 'JWT' or 'JOSE'.
        """
        if not headers:
            raise ValueError(INVALID_INPUT_ERROR.format('header cannot be empty'))

        alg = headers.get('alg')
        if not alg:
            raise ValueError(INVALID_INPUT_ERROR.format('header alg cannot be empty'))

        if alg not in self._SUPPORTED_ALGORITHMS:
            raise InvalidAlgorithmError(alg)

        typ = headers.get('typ')
        if typ and typ not in self._SUPPORTED_TYPES:
            raise InvalidTypeError(typ)

    def validate_claims(
        self, payload: Dict[str, Any], expected_audience: Set[str]
    ) -> None:
        """Validates payload for required claims (aud, exp, sub).

        Args:
            payload: Token payload.
            expected_audience: Audience as a Set of strings used to validate the 'aud' claim.

        Returns:
            None

        Raises:
            MissingClaimError: In case a required claim is not present.
            InvalidClaimError: In case a claim contains an invalid value or expected_audience is not a subset of audience_claim.
            TokenExpiredError: In case token is expired.
            ValueError: In case expected_audience is empty.
        """
        for claim in self._REQUIRED_CLAIMS:
            if not payload.get(claim):
                raise MissingClaimError(claim)

        self._validate_exp(str(payload.get('exp')))
        self._validate_aud(payload.get('aud', []), expected_audience)

    def _validate_exp(self, expiration_date: str) -> None:
        """Verifies expiration.

        Note: If and when https://github.com/jpadilla/pyjwt/issues/599 is fixed, this can be simplified/removed.

        Args:
            expiration_date: Date to check if it is expired.

        Raises:
            TokenExpiredError: In case it is expired.
        """
        int_date = int(expiration_date)
        utctime = timegm(datetime.datetime.utcnow().utctimetuple())
        if int_date < utctime:
            raise TokenExpiredError()

    def _validate_aud(
        self, audience_claim: List[str], expected_audience: Set[str]
    ) -> None:
        """Verifies if expected_audience is present in audience_claim. The aud claim MUST be present.

        Args:
            audience_claim: List of token's audience claim to be validated.
            expected_audience: Set of the claims expected to be present in the token's audience claim.

        Raises:
            InvalidClaimError: In expected_audience is not a subset of audience_claim or it is empty.
            ValueError: In case expected_audience is empty.
        """
        if not expected_audience:
            raise ValueError(
                INVALID_INPUT_ERROR.format('expected_audience cannot be empty')
            )

        if not audience_claim or all(aud == '' for aud in audience_claim):
            raise InvalidClaimError('audience_claim cannot be empty')

        if not all(aud in audience_claim for aud in expected_audience):
            raise InvalidClaimError(AUDIENCE_NOT_MATCH_ERROR)
