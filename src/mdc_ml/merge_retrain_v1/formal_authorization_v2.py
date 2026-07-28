from __future__ import annotations

from dataclasses import dataclass

SCOPES = {
    "FORMAL_CLASSIFICATION_OOF_ONLY": {"classification_oof"},
    "FORMAL_REGRESSION_OOF_ONLY": {"regression_oof"},
    "FINAL_CLASSIFIER_ONLY": {"final_classifier"},
    "FINAL_REGRESSOR_ONLY": {"final_regressor"},
    "EVALUATION_ONLY": {"evaluation"},
    "BOOTSTRAP_ONLY": {"bootstrap"},
    "PROMOTION_ROUTE_ONLY": {"promotion", "route"},
}

@dataclass(frozen=True)
class Authorization:
    scope: str
    def permits(self, stage: str) -> bool: return stage in SCOPES.get(self.scope, set())

def require(authorization: Authorization, stage: str) -> None:
    if not authorization.permits(stage):
        raise RuntimeError("AUTHORIZATION_SCOPE_NOT_GRANTED:" + stage)
