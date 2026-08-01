import base64
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "public_safety.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("subject_public_safety", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


public_safety = _load_module()


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "api.key",
        "api-key",
        "AWS.SECRET-ACCESS_KEY",
        "raw-evidence",
        "private.path",
    ],
)
def test_rejects_nested_forbidden_key_separator_variants(key):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"outer": [{"metadata": {key: "redacted"}}]})


@pytest.mark.parametrize(
    "key",
    [
        "access_token",
        "apiKey",
        "clientSecret",
        "api key",
        "openai_api_key",
        "authorization",
    ],
)
def test_rejects_nested_normalized_and_namespaced_forbidden_keys(key):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"outer": [{"metadata": {key: "redacted"}}]})


@pytest.mark.parametrize(
    "key",
    [
        "OpenAIAPIKey",
        "openAIAPIKey",
        "OPENAIAPIKey",
        "OpenAIAccessToken",
        "OpenAIClientSecret",
        "AWSSecretAccessKey",
        "HTTPAuthorization",
    ],
)
def test_rejects_acronym_namespaced_forbidden_keys(key):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"metadata": {key: "redacted"}})


@pytest.mark.parametrize(
    "value",
    [
        "OpenAI" + "API" + "Key" + "=" + "placeholder",
        "OpenAI" + "Access" + "Token" + "=" + "placeholder",
        "OpenAI" + "Client" + "Secret" + "=" + "placeholder",
        "service" + "Secret" + "=" + "placeholder",
        "client" + "_" + "secret" + ":" + " placeholder",
    ],
)
def test_rejects_assignment_shaped_sensitive_keys(value):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": value})


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/docs?" + "OpenAI" + "API" + "Key" + "=" + "placeholder",
        "https://example.com/docs?" + "OpenAI" + "Access" + "Token" + "=" + "placeholder",
        "https://example.com/docs?" + "OpenAI" + "Client" + "Secret" + "=" + "placeholder",
        "https://example.com/docs?" + "service" + "Secret" + "=" + "placeholder",
        "https://example.com/docs?" + "OpenAI" + "+" + "API" + "+" + "Key" + "=" + "placeholder",
        "https://example.com/docs#" + "OpenAI" + "API" + "Key" + "=" + "placeholder",
        "https://example.com/docs#" + "OpenAI" + "+" + "API" + "+" + "Key" + "=" + "placeholder",
        "https://example.com/docs#" + "client" + "_" + "secret" + "=" + "placeholder",
    ],
)
def test_rejects_url_query_or_fragment_sensitive_assignments(value):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": value})


@pytest.mark.parametrize(
    "value",
    [
        "{" + "\"" + "OpenAI" + "API" + "Key" + "\"" + ":" + "\"placeholder\"" + "}",
        "{" + "\"" + "api" + "_" + "key" + "\"" + ":" + "\"placeholder\"" + "}",
        "'" + "client" + "_" + "secret" + "'" + ":" + " 'placeholder'",
        "config[" + "\"" + "OPENAI" + "_" + "API" + "_" + "KEY" + "\"" + "]=" + "\"placeholder\"",
    ],
)
def test_rejects_quoted_or_bracketed_sensitive_assignments(value):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": value})


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/docs?note=" + "Bear" + "er" + "+" + "safeLookingValue123",
        "https://example.com/docs?note=" + "Bear" + "er" + "%20" + "safeLookingValue123",
        "https://example.com/docs?next=%2Fvar%2Ftmp%2Fitem",
        "https://example.com/docs#next=/var/tmp/item",
    ],
)
def test_rejects_decoded_url_component_sensitive_carriers(value):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": value})


@pytest.mark.parametrize(
    "key",
    ["monkey", "authorization_policy", "api_key_rotation_policy", "token_count"],
)
def test_allows_legal_neighbor_keys(key):
    public_safety.validate_public_safe({"outer": [{"metadata": {key: "public"}}]})


def test_rejects_non_string_dictionary_keys():
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"outer": [{1: "public"}]})


def _credential_carriers():
    suffix = "a1B2c3D4e5F6g7H8"
    return [
        "gh" + "p_" + suffix,
        "github" + "_pat_" + suffix,
        "gl" + "pat-" + suffix,
        "sk" + "_live_" + suffix,
        "AK" + "IA" + suffix,
        "AI" + "za" + suffix,
        "gh" + "o_short",
        "xo" + "xb-short",
    ]


@pytest.mark.parametrize("value", _credential_carriers())
def test_rejects_long_and_short_credential_prefixes(value):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": value})


def _secret_carriers():
    segment = "abcdefghijk"
    return [
        "Bear" + "er " + "safeLookingValue123",
        "Bear" + "er " + "abc.def.ghi",
        segment + "." + segment.upper() + "." + "0123456789_",
        "api" + "-key = harmless-placeholder",
        "-----BEGIN " + "PRIVATE KEY-----\nplaceholder",
    ]


@pytest.mark.parametrize("value", _secret_carriers())
def test_rejects_bearer_jwt_assignment_and_private_key_carriers(value):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe([{"value": value}])


def test_rejects_basic_authorization_credential_carrier():
    payload = "YWJj" + "OmRlZg=="
    carrier = "Basic " + payload

    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": carrier})


@pytest.mark.parametrize(
    "username",
    ["public-user", "publicuser"],
    ids=["requested-placeholder", "letters-only-unpadded"],
)
def test_rejects_unpadded_basic_authorization_credential_carrier(username):
    credential = f"{username}:placeholder".encode("ascii")
    payload = base64.b64encode(credential).decode("ascii").rstrip("=")
    if username == "publicuser":
        assert payload.isalpha()
    carrier = "Basic " + payload

    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": carrier})


@pytest.mark.parametrize("separator", [":", ".", "_", "-"])
def test_rejects_bearer_punctuation_letter_carrier(separator):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": "Bearer" + separator + "abcdefghijklmnop"})


@pytest.mark.parametrize(
    "carrier",
    [
        "https://public-user:example-credential@example.com/docs",
        "https://:example-credential@example.com/docs",
        "https://public-user:@example.com/docs",
        "https://public-user@example.com/docs",
        "https://public-user%3Aexample-credential@example.com/docs",
    ],
)
def test_rejects_http_url_userinfo_credential_carrier(carrier):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": carrier})


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/public:path?label=key:value",
        "Basic education remains public.",
        "Basic !!!! remains noncredential prose.",
        "ASIAN PUBLIC HISTORY",
        "Bearer responsibilities remain documented.",
        "Asian public history",
        "The bearer of good news",
        "Bearer credentials remain confidential.",
        "Bearer credentials remain documented.",
        "api_key_rotation_policy = public",
        "authorization_policy: public",
    ],
)
def test_allows_credential_carrier_legal_neighbors(value):
    public_safety.validate_public_safe({"value": value})


def _path_carriers():
    slash = "/"
    backslash = "\\"
    return [
        slash + "var" + slash + "tmp" + slash + "item",
        "logs" + slash + slash + "private" + slash + "item",
        "C:" + backslash + "Users" + backslash + "item",
        backslash + backslash + "server" + backslash + "share",
        "file:" + slash + slash + slash + "tmp" + slash + "item",
        "~" + slash + ".config" + slash + "item",
    ]


@pytest.mark.parametrize("value", _path_carriers())
def test_rejects_local_path_carriers(value):
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe({"value": value})


def test_rejects_nul():
    with pytest.raises(public_safety.PublicSafetyError):
        public_safety.validate_public_safe("public" + chr(0) + "text")


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/public/design?id=42",
        "https://example.com/public//design",
        "https://example.com/docs?next=/public/design",
        "https://example.com/docs#section=/public/design",
        "https://example.com/docs#section=file:format",
        "http://localhost:8000/docs",
        "scripts/public_safety.py",
        "docs/subject-distillation.md",
        "issue-410-public-slice",
        "01J8Y4X7N3Q2R5T6V9W0ABCD12",
        "The project owner may ask a reviewer to verify this public claim.",
        {"claims": ["Evidence remains attributable.", {"status": "proposed"}]},
    ],
)
def test_allows_public_values(value):
    public_safety.validate_public_safe(value)


def test_error_is_fixed_and_does_not_echo_hostile_payload():
    hostile = "Bear" + "er " + "do-not-echo-this-value"

    with pytest.raises(public_safety.PublicSafetyError) as caught:
        public_safety.validate_public_safe({"value": hostile})

    assert str(caught.value) == "public-safety validation failed"
    assert hostile not in str(caught.value)


@pytest.mark.parametrize(
    "value",
    ["https://[", "https://[invalid", "prefix https://[]/docs"],
)
def test_malformed_http_urls_fail_closed_with_fixed_diagnostic(value):
    with pytest.raises(public_safety.PublicSafetyError) as caught:
        public_safety.validate_public_safe({"value": value})

    assert str(caught.value) == "public-safety validation failed"


@pytest.mark.parametrize(
    "value",
    [
        ("public",),
        {"public"},
        b"public",
        object(),
        math.nan,
        math.inf,
        -math.inf,
    ],
    ids=["tuple", "set", "bytes", "object", "nan", "positive-inf", "negative-inf"],
)
def test_rejects_non_json_or_non_finite_values_with_fixed_diagnostic(value):
    with pytest.raises(public_safety.PublicSafetyError) as caught:
        public_safety.validate_public_safe({"value": value})

    assert str(caught.value) == "public-safety validation failed"


@pytest.mark.parametrize("container_type", [dict, list])
def test_rejects_cycles_with_fixed_diagnostic(container_type):
    if container_type is dict:
        value = {}
        value["cycle"] = value
    else:
        value = []
        value.append(value)

    with pytest.raises(public_safety.PublicSafetyError) as caught:
        public_safety.validate_public_safe(value)

    assert str(caught.value) == "public-safety validation failed"


def test_allows_acyclic_shared_substructure():
    shared = {"status": "public"}
    public_safety.validate_public_safe({"first": shared, "second": shared})
