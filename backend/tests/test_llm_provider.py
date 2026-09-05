"""Provider selection in config.py: which LLM backend answers Ángela's calls,
chosen by configuration (LLM_PROVIDER + credentials), never by code edits.

Regression cover for the concrete bug this feature fixes: a correctly
configured AI Gateway (ANTHROPIC_API_KEY deliberately EMPTY, credential lives
in AI_GATEWAY_API_KEY) must NOT fall through to offline — modo() must
report 'claude'.

No test in this file makes a network call: the SDK constructor is
monkeypatched to capture kwargs instead of connecting anywhere.
"""
import config as config_module


def _clear_llm_env(monkeypatch):
    # Credentials come from config itself, so adding a provider can't leave a
    # stale credential set here and quietly configure a provider a test
    # believes is absent.
    for var in (*config_module.credential_vars(), "LLM_PROVIDER",
                "AI_GATEWAY_BASE_URL", "ANGELA_MODEL", "GATEWAY_MODEL"):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# Provider resolution (_resolve_provider / provider() / model_disponible())
# ---------------------------------------------------------------------------

def test_explicit_anthropic_with_key_selects_anthropic(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert config_module.provider() == "anthropic"
    assert config_module.model_disponible() is True


def test_explicit_gateway_with_key_selects_gateway(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gateway")
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    assert config_module.provider() == "gateway"
    assert config_module.model_disponible() is True


def test_explicit_provider_without_its_own_credential_is_not_configured(monkeypatch):
    """An explicit LLM_PROVIDER must not silently borrow the OTHER provider's
    credential — 'gateway' with only a direct key configured stays unusable."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gateway")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert config_module.provider() is None
    assert config_module.model_disponible() is False
    assert config_module.modo() == "offline"


def test_autodetect_direct_key_only_selects_anthropic(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert config_module.provider() == "anthropic"


def test_autodetect_gateway_key_only_selects_gateway(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    assert config_module.provider() == "gateway"


def test_autodetect_both_configured_ties_break_to_anthropic(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    assert config_module.provider() == "anthropic"


def test_autodetect_neither_configured_falls_back(monkeypatch):
    _clear_llm_env(monkeypatch)
    assert config_module.provider() is None
    assert config_module.model_disponible() is False
    assert config_module.modo() == "offline"


def test_gateway_with_empty_anthropic_api_key_reports_claude_mode(monkeypatch):
    """The exact bug being fixed: ANTHROPIC_API_KEY is deliberately EMPTY (a
    correctly configured gateway deployment), the credential lives in
    AI_GATEWAY_API_KEY — modo() must say 'claude', not 'offline'."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    assert config_module.provider() == "gateway"
    assert config_module.modo() == "claude"


def test_unrecognized_llm_provider_value_falls_back_to_autodetect(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "bogus-provider")
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    assert config_module.provider() == "gateway"


# ---------------------------------------------------------------------------
# Client construction: correct transport per provider, no network calls.
# ---------------------------------------------------------------------------

class _FakeAnthropicClient:
    """Captures constructor kwargs instead of talking to any network."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def _patch_anthropic_constructor(monkeypatch):
    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropicClient)


def test_get_client_uses_api_key_for_anthropic_provider(monkeypatch):
    _clear_llm_env(monkeypatch)
    _patch_anthropic_constructor(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    client = config_module.get_client()
    assert isinstance(client, _FakeAnthropicClient)
    assert client.kwargs.get("api_key") == "sk-ant-test"
    assert "auth_token" not in client.kwargs
    assert "base_url" not in client.kwargs


def test_get_client_uses_auth_token_and_base_url_for_gateway(monkeypatch):
    """Getting this wrong (api_key= instead of auth_token=) yields a 401 that
    looks like a bad key — the gateway authenticates via Bearer, not x-api-key."""
    _clear_llm_env(monkeypatch)
    _patch_anthropic_constructor(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gateway")
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")

    client = config_module.get_client()
    assert isinstance(client, _FakeAnthropicClient)
    assert client.kwargs.get("auth_token") == "gw-test-key"
    assert client.kwargs.get("base_url") == "https://ai-gateway.vercel.sh"
    assert "api_key" not in client.kwargs


def test_get_client_respects_explicit_gateway_base_url(monkeypatch):
    _clear_llm_env(monkeypatch)
    _patch_anthropic_constructor(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gateway")
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    monkeypatch.setenv("AI_GATEWAY_BASE_URL", "https://custom.gateway.example")

    client = config_module.get_client()
    assert client.kwargs.get("base_url") == "https://custom.gateway.example"


def test_get_client_returns_none_when_no_provider_configured(monkeypatch):
    _clear_llm_env(monkeypatch)
    _patch_anthropic_constructor(monkeypatch)
    assert config_module.get_client() is None


# ---------------------------------------------------------------------------
# Model slug resolution: per-provider default, explicit override wins.
# ---------------------------------------------------------------------------

def test_default_model_is_hyphenated_for_anthropic(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert config_module.modelo_validacion() == "claude-sonnet-4-6"


def test_default_model_is_prefixed_and_dotted_for_gateway(monkeypatch):
    """A hyphenated slug through the gateway returns HTTP 400 — the default
    must translate to the provider-prefixed, dotted-version slug."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    assert config_module.modelo_validacion() == "anthropic/claude-sonnet-4.6"


def test_explicit_angela_model_overrides_and_is_never_rewritten(monkeypatch):
    """An explicit ANGELA_MODEL must pass through untouched, even one shaped
    for the OTHER provider — only the module's own default gets translated."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    monkeypatch.setenv("ANGELA_MODEL", "claude-haiku-4-5")
    assert config_module.modelo_validacion() == "claude-haiku-4-5"


def test_gateway_model_wins_over_angela_model_on_the_gateway(monkeypatch):
    """One .env holds both slug shapes at once: the direct-Anthropic
    ANGELA_MODEL and the prefixed+dotted GATEWAY_MODEL. Through the gateway
    the gateway-shaped one must win, or the hyphenated slug 400s."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    monkeypatch.setenv("ANGELA_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("GATEWAY_MODEL", "anthropic/claude-sonnet-5")
    assert config_module.modelo_validacion() == "anthropic/claude-sonnet-5"


def test_gateway_model_is_ignored_by_the_direct_provider(monkeypatch):
    """The mirror image: a gateway-shaped GATEWAY_MODEL must never leak into
    a direct-Anthropic call, which only honours ANGELA_MODEL."""
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("GATEWAY_MODEL", "anthropic/claude-sonnet-5")
    assert config_module.modelo_validacion() == "claude-sonnet-4-6"


def test_modelo_para_delegates_to_modelo_validacion_when_routing_off(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-test-key")
    assert config_module.ROUTING_ACTIVO is False
    assert config_module.modelo_para() == "anthropic/claude-sonnet-4.6"
