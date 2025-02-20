import pytest
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.backends import default_backend
from jwt.exceptions import InvalidKeyError
from pyspiffe.bundle.jwt_bundle.jwt_bundle import JwtBundle
from pyspiffe.bundle.jwt_bundle.exceptions import JwtBundleError, ParseJWTBundleError
from pyspiffe.exceptions import ArgumentError
from pyspiffe.spiffe_id.spiffe_id import TrustDomain
from test.utils.utils import (
    JWKS_1_EC_KEY,
    JWKS_2_EC_1_RSA_KEYS,
    JWKS_MISSING_X,
    JWKS_MISSING_KEY_ID,
)

# Default trust domain to run test cases.
trust_domain = TrustDomain.parse("spiffe://any.domain")

# Default authorities to run test cases.
ec_key = ec.generate_private_key(ec.SECP384R1(), default_backend())
rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
authorities = {
    'kid1': ec_key,
    'kid2': rsa_key,
}


def test_create_jwt_bundle():
    jwt_bundle = JwtBundle(trust_domain, authorities)

    assert jwt_bundle.trust_domain() == trust_domain
    assert len(jwt_bundle.jwt_authorities().keys()) == len(authorities.keys())


def test_create_jwt_bundle_no_trust_domain():
    with pytest.raises(JwtBundleError) as exc_info:
        JwtBundle(None, authorities)

    assert str(exc_info.value) == 'Trust domain is missing.'


def test_create_jwt_bundle_no_authorities():
    jwt_bundle = JwtBundle(trust_domain, None)

    assert jwt_bundle.trust_domain() == trust_domain
    assert isinstance(jwt_bundle.jwt_authorities(), dict)
    assert len(jwt_bundle.jwt_authorities().keys()) == 0


"""
    get_jwt_authority
"""


def test_get_jwt_authority_valid_input():
    jwt_bundle = JwtBundle(trust_domain, authorities)

    authority_key = jwt_bundle.get_jwt_authority('kid2')

    assert rsa_key == authority_key


def test_get_jwt_authority_invalid_key_id_not_found():
    jwt_bundle = JwtBundle(trust_domain, authorities)

    response = jwt_bundle.get_jwt_authority('p0')

    assert response is None


def test_get_jwt_authority_invalid_input():
    jwt_bundle = JwtBundle(trust_domain, authorities)

    with pytest.raises(ArgumentError) as exception:
        jwt_bundle.get_jwt_authority('')

    assert str(exception.value) == 'key_id cannot be empty.'


def test_get_jwt_authority_empty_authority_dict():
    invalid_authorities = None
    jwt_bundle = JwtBundle(trust_domain, invalid_authorities)

    response = jwt_bundle.get_jwt_authority(key_id='p1')

    assert response is None


@pytest.mark.parametrize(
    'test_bytes, expected_authorities',
    [(JWKS_1_EC_KEY, 1), (JWKS_2_EC_1_RSA_KEYS, 3)],
)
def test_parse(test_bytes, expected_authorities):
    jwt_bundle = JwtBundle.parse(trust_domain, test_bytes)

    assert jwt_bundle
    assert len(jwt_bundle.jwt_authorities()) == expected_authorities


@pytest.mark.parametrize(
    'test_trust_domain',
    ['', None],
)
def test_parse_invalid_trust_domain(test_trust_domain):
    with pytest.raises(ArgumentError) as exception:
        JwtBundle.parse(test_trust_domain, JWKS_1_EC_KEY)

    assert str(exception.value) == 'Trust domain is missing.'


@pytest.mark.parametrize(
    'test_bundle_bytes',
    [b'', None],
)
def test_parse_missing_bundle_bytes(test_bundle_bytes):
    with pytest.raises(ArgumentError) as exception:
        JwtBundle.parse(trust_domain, test_bundle_bytes)

    assert str(exception.value) == 'Bundle bytes cannot be empty.'


@pytest.mark.parametrize(
    'test_bytes',
    [b'1211', b'invalid bytes'],
)
def test_parse_invalid_bytes(test_bytes):
    with pytest.raises(ParseJWTBundleError) as exception:
        JwtBundle.parse(trust_domain, test_bytes)

    assert (
        str(exception.value)
        == 'Error parsing JWT bundle: Cannot parse jwks. bundle_bytes does not represent a valid jwks.'
    )


def test_parse_bundle_bytes_invalid_key(mocker):
    mocker.patch(
        'pyspiffe.bundle.jwt_bundle.jwt_bundle.PyJWKSet.from_json',
        side_effect=InvalidKeyError('Invalid Key'),
        autospect=True,
    )

    with pytest.raises(ParseJWTBundleError) as exception:
        JwtBundle.parse(trust_domain, JWKS_MISSING_X)

    assert (
        str(exception.value)
        == 'Error parsing JWT bundle: Cannot parse jwks from bundle_bytes: Invalid Key.'
    )


def test_parse_corrupted_key_missing_key_id():
    with pytest.raises(ParseJWTBundleError) as exception:
        JwtBundle.parse(trust_domain, JWKS_MISSING_KEY_ID)

    assert (
        str(exception.value)
        == 'Error parsing JWT bundle: Error adding authority from JWKS: keyID cannot be empty.'
    )
