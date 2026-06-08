from __future__ import annotations

from .compat import build_compatibility_matrix, model_runtime_compatibility
from .download import (
    default_cache_root,
    list_pulled_models,
    load_chat_session,
    pull_model,
    run_pulled_model,
)
from .gateway import (
    build_chat_route_response,
    build_models_response,
    route_chat_payload,
    routing_request_from_chat_payload,
)
from .ops import (
    cache_report,
    default_state_root,
    diff_model_registry,
    hardware_recommendations,
    inspect_hardware,
    remote_artifact_metadata,
    sha256_file,
    verify_cache,
    write_hash_manifest,
)
from .platform import (
    build_agent_bridge_config,
    build_opencode_provider_config,
    build_registry_analytics,
    catalog_models,
    compare_models,
    recommend_model,
    render_hpe_apptainer_definition,
    render_hpe_gateway_config,
    render_hpe_readme,
    render_hpe_slurm_script,
    route_scenario_matrix,
)
from .registry import ModelEndpoint, RoutingRequest, load_model_registry
from .router import RouteDecision, SovereignModelRouter
from .server import handle_gateway_request, load_gateway_config, smoke_gateway
from .ui import smoke_ui as smoke_ui

__all__ = [
    "ModelEndpoint",
    "RouteDecision",
    "RoutingRequest",
    "SovereignModelRouter",
    "build_agent_bridge_config",
    "build_chat_route_response",
    "build_compatibility_matrix",
    "build_models_response",
    "build_opencode_provider_config",
    "build_registry_analytics",
    "cache_report",
    "catalog_models",
    "compare_models",
    "default_cache_root",
    "default_state_root",
    "diff_model_registry",
    "hardware_recommendations",
    "handle_gateway_request",
    "inspect_hardware",
    "list_pulled_models",
    "load_chat_session",
    "load_gateway_config",
    "load_model_registry",
    "model_runtime_compatibility",
    "pull_model",
    "recommend_model",
    "remote_artifact_metadata",
    "render_hpe_apptainer_definition",
    "render_hpe_gateway_config",
    "render_hpe_readme",
    "render_hpe_slurm_script",
    "route_chat_payload",
    "route_scenario_matrix",
    "routing_request_from_chat_payload",
    "run_pulled_model",
    "sha256_file",
    "smoke_gateway",
    "smoke_ui",
    "verify_cache",
    "write_hash_manifest",
]
