"""Shared test fixtures for ringsnap_ops_flow tests."""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# Lightweight local stubs so tests can run without external deps in CI sandboxes.

if importlib.util.find_spec("pydantic") is None and "pydantic" not in sys.modules:
    pydantic_stub = types.ModuleType("pydantic")

    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def Field(default=None, **_kwargs):
        return default

    pydantic_stub.BaseModel = BaseModel
    pydantic_stub.Field = Field
    sys.modules["pydantic"] = pydantic_stub

if importlib.util.find_spec("yaml") is None and "yaml" not in sys.modules:
    yaml_stub = types.ModuleType("yaml")
    yaml_stub.safe_load = lambda _stream: {}
    sys.modules["yaml"] = yaml_stub

if importlib.util.find_spec("crewai") is None and "crewai" not in sys.modules:
    crewai_stub = types.ModuleType("crewai")

    class Agent:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.tools = kwargs.get("tools", [])

    class Task:
        def __init__(self, description: str, expected_output: str, agent):
            self.description = description
            self.expected_output = expected_output
            self.agent = agent

    class Crew:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def kickoff(self):
            return "stubbed"

    class Process:
        sequential = "sequential"

    crewai_stub.Agent = Agent
    crewai_stub.Task = Task
    crewai_stub.Crew = Crew
    crewai_stub.Process = Process
    sys.modules["crewai"] = crewai_stub

if "crewai.flow" not in sys.modules:
    crewai_flow_stub = types.ModuleType("crewai.flow")
    sys.modules["crewai.flow"] = crewai_flow_stub

if "crewai.flow.flow" not in sys.modules:
    crewai_flow_flow_stub = types.ModuleType("crewai.flow.flow")

    class Flow:
        def __init__(self, *args, **kwargs):
            pass

        def __class_getitem__(cls, _item):
            return cls

    def start(*_args, **_kwargs):
        def deco(fn):
            return fn
        return deco

    crewai_flow_flow_stub.Flow = Flow
    crewai_flow_flow_stub.start = start
    sys.modules["crewai.flow.flow"] = crewai_flow_flow_stub


if "crewai.tools" not in sys.modules:
    tools_stub = types.ModuleType("crewai.tools")

    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    tools_stub.BaseTool = BaseTool
    sys.modules["crewai.tools"] = tools_stub


if importlib.util.find_spec("fastapi") is None and "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class BackgroundTasks:
        def add_task(self, _fn, *_args, **_kwargs):
            return None

    class Request:
        headers = {}

        async def json(self):
            return {}

    class FastAPI:
        def __init__(self, **_kwargs):
            pass

        def get(self, _path):
            def deco(fn):
                return fn
            return deco

        def post(self, _path):
            def deco(fn):
                return fn
            return deco

    def Depends(dep=None):
        return dep

    fastapi_stub.FastAPI = FastAPI
    fastapi_stub.HTTPException = HTTPException
    fastapi_stub.BackgroundTasks = BackgroundTasks
    fastapi_stub.Request = Request
    fastapi_stub.Depends = Depends
    sys.modules["fastapi"] = fastapi_stub

if "fastapi.responses" not in sys.modules:
    fastapi_responses_stub = types.ModuleType("fastapi.responses")

    class JSONResponse:
        def __init__(self, content=None, status_code: int = 200):
            self.content = content
            self.status_code = status_code

    fastapi_responses_stub.JSONResponse = JSONResponse
    sys.modules["fastapi.responses"] = fastapi_responses_stub



@pytest.fixture
def stub_supabase():
    """Stub Supabase adapter that returns empty results."""
    from ringsnap_ops_flow.adapters.supabase_adapter import SupabaseAdapter

    return SupabaseAdapter()  # No URL/key = stub mode


@pytest.fixture
def stub_stripe():
    from ringsnap_ops_flow.adapters.stripe_adapter import StripeAdapter

    return StripeAdapter()  # No key = stub mode


@pytest.fixture
def stub_twilio():
    from ringsnap_ops_flow.adapters.twilio_adapter import TwilioAdapter

    return TwilioAdapter()  # No credentials = stub mode


@pytest.fixture
def signup_handler(stub_supabase, stub_stripe, stub_twilio):
    from ringsnap_ops_flow.deterministic.signup_handler import SignupHandler

    return SignupHandler(
        supabase_adapter=stub_supabase,
        stripe_adapter=stub_stripe,
        twilio_adapter=stub_twilio,
    )


@pytest.fixture
def payment_handler(stub_supabase, stub_stripe):
    from ringsnap_ops_flow.deterministic.payment_handler import PaymentHandler

    return PaymentHandler(supabase_adapter=stub_supabase, stripe_adapter=stub_stripe)


@pytest.fixture
def provisioning_handler(stub_supabase):
    from ringsnap_ops_flow.deterministic.provisioning_handler import ProvisioningHandler

    return ProvisioningHandler(supabase_adapter=stub_supabase)


@pytest.fixture
def onboarding_handler(stub_supabase):
    from ringsnap_ops_flow.deterministic.onboarding_handler import OnboardingHandler

    return OnboardingHandler(supabase_adapter=stub_supabase)


@pytest.fixture
def funnel_tracker():
    from ringsnap_ops_flow.deterministic.funnel_tracker import FunnelTracker

    return FunnelTracker()  # No adapter = stub mode


@pytest.fixture
def event_gate():
    from ringsnap_ops_flow.event_gate import EventGate

    gate = EventGate()
    gate.reset_daily_counters()
    return gate


@pytest.fixture
def sample_lead_data():
    return {
        "contact_name": "John Smith",
        "contact_email": "john@smithplumbing.com",
        "contact_phone": "+15555550101",
        "business_name": "Smith Plumbing",
        "trade": "plumbing",
        "selected_plan": "core",
        "expressed_urgency": True,
        "monthly_calls": 80,
    }
