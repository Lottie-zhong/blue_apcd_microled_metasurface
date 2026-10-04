"""Frozen K6 V2 regressors and train-only normalization."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import numpy as np
from sklearn.kernel_ridge import KernelRidge
from .contracts import C_HAT_REAL_OUTPUTS, MODEL_OUTPUTS, pack_model_target, unpack_model_target

KRR_GAMMAS = (1.0 / 6.0, 1.0 / 3.0, 2.0 / 3.0)
KRR_RIDGE_ALPHAS = (1e-4, 1e-2, 1.0)
MLP_WEIGHT_DECAYS = (1e-5, 1e-4, 1e-3)
MLP_SEEDS = (0, 1, 2)
MLP_HIDDEN_WIDTH = 32
MLP_MAX_UPDATES = 1000
MLP_EARLY_STOP_PATIENCE = 50
MLP_EARLY_STOP_MIN_DELTA = 1e-5
EXPECTED_MLP_PARAMETERS = 21377


def _matrix(values: np.ndarray, name: str, cols: int) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != cols:
        raise ValueError(f"{name}_shape_must_be_Nx{cols}")
    if arr.shape[0] == 0:
        raise ValueError(f"{name}_empty")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name}_nonfinite")
    return arr


@dataclass(frozen=True)
class GeometryStandardizer:
    """Mean/std of six ordered D coordinates, fit only on current train groups."""
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, X: np.ndarray) -> "GeometryStandardizer":
        x = _matrix(X, "geometry", 6)
        mean = x.mean(axis=0, dtype=np.float64)
        scale = x.std(axis=0, ddof=0, dtype=np.float64)
        if not np.isfinite(mean).all() or not np.isfinite(scale).all():
            raise ValueError("geometry_standardizer_nonfinite")
        # V2 has no fitted scale floor: a constant training coordinate fails closed.
        if (scale <= 0.0).any():
            raise ValueError("geometry_training_coordinate_has_zero_std")
        return cls(mean, scale)

    def transform(self, X: np.ndarray) -> np.ndarray:
        out = (_matrix(X, "geometry", 6) - self.mean) / self.scale
        if not np.isfinite(out).all():
            raise ValueError("standardized_geometry_nonfinite")
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {"mean": self.mean.tolist(), "scale": self.scale.tolist()}


@dataclass(frozen=True)
class V2TargetNormalizer:
    """588 channel C means/shared residual RMS and scalar log-P mean/std."""
    c_mean: np.ndarray
    c_shared_rms: float
    log_p_mean: float
    log_p_std: float

    @classmethod
    def fit(cls, packed_targets: np.ndarray) -> "V2TargetNormalizer":
        y = _matrix(packed_targets, "packed_target", MODEL_OUTPUTS)
        c, lp = y[:, :C_HAT_REAL_OUTPUTS], y[:, C_HAT_REAL_OUTPUTS:]
        c_mean = c.mean(axis=0, dtype=np.float64)
        c_rms = float(np.sqrt(np.mean(np.square(c - c_mean[None, :]), dtype=np.float64)))
        lp_mean = float(np.mean(lp, dtype=np.float64))
        lp_std = float(np.std(lp, ddof=0, dtype=np.float64))
        if not np.isfinite(c_mean).all() or not np.isfinite([c_rms, lp_mean, lp_std]).all():
            raise ValueError("target_training_statistics_nonfinite")
        if c_rms <= 0.0 or lp_std <= 0.0:
            raise ValueError("target_training_statistics_degenerate_no_scale_floor")
        return cls(c_mean, c_rms, lp_mean, lp_std)

    def transform(self, packed_targets: np.ndarray) -> np.ndarray:
        y = _matrix(packed_targets, "packed_target", MODEL_OUTPUTS)
        out = np.empty_like(y)
        out[:, :C_HAT_REAL_OUTPUTS] = (y[:, :C_HAT_REAL_OUTPUTS] - self.c_mean) / self.c_shared_rms
        out[:, C_HAT_REAL_OUTPUTS:] = (y[:, C_HAT_REAL_OUTPUTS:] - self.log_p_mean) / self.log_p_std
        if not np.isfinite(out).all():
            raise ValueError("normalized_target_nonfinite")
        return out

    def inverse_transform(self, normalized_targets: np.ndarray) -> np.ndarray:
        y = _matrix(normalized_targets, "normalized_target", MODEL_OUTPUTS)
        out = np.empty_like(y)
        out[:, :C_HAT_REAL_OUTPUTS] = y[:, :C_HAT_REAL_OUTPUTS] * self.c_shared_rms + self.c_mean
        out[:, C_HAT_REAL_OUTPUTS:] = y[:, C_HAT_REAL_OUTPUTS:] * self.log_p_std + self.log_p_mean
        if not np.isfinite(out).all():
            raise ValueError("inverse_normalized_target_nonfinite")
        return out

    def loss_components(self, pred: np.ndarray, truth: np.ndarray) -> Tuple[float, float, float]:
        p = _matrix(pred, "normalized_prediction", MODEL_OUTPUTS)
        y = _matrix(truth, "normalized_target", MODEL_OUTPUTS)
        if p.shape != y.shape:
            raise ValueError("normalized_loss_shape_mismatch")
        lc = float(np.mean(np.square(p[:, :C_HAT_REAL_OUTPUTS] - y[:, :C_HAT_REAL_OUTPUTS])))
        lp = float(np.mean(np.square(p[:, C_HAT_REAL_OUTPUTS:] - y[:, C_HAT_REAL_OUTPUTS:])))
        return lc, lp, lc + lp

    def to_dict(self) -> Dict[str, Any]:
        return {"c_mean": self.c_mean.tolist(), "c_shared_rms": self.c_shared_rms,
                "log_p_mean": self.log_p_mean, "log_p_std": self.log_p_std}


def pack_case_target(c_hat: np.ndarray, p_scale: np.ndarray) -> np.ndarray:
    y = pack_model_target(c_hat, p_scale)
    if y.shape != (1, MODEL_OUTPUTS):
        raise ValueError("shared_target_packer_returned_unexpected_shape")
    return y[0]


def unpack_prediction(raw_packed_prediction: np.ndarray):
    c, p = unpack_model_target(raw_packed_prediction)
    if not (np.isfinite(c.real).all() and np.isfinite(c.imag).all()):
        raise ValueError("predicted_c_hat_nonfinite")
    if not np.isfinite(p).all() or (p <= 0.0).any():
        raise ValueError("predicted_p_scale_not_finite_positive")
    return c, p


class RBFKRR:
    """One grid point; C and log-P regressions share gamma and ridge alpha."""
    def __init__(self, gamma: float, ridge_alpha: float):
        if gamma not in KRR_GAMMAS:
            raise ValueError("krr_gamma_not_in_frozen_grid")
        if ridge_alpha not in KRR_RIDGE_ALPHAS:
            raise ValueError("krr_ridge_alpha_not_in_frozen_grid")
        self.gamma, self.ridge_alpha = float(gamma), float(ridge_alpha)
        self._c = self._p = None

    def fit(self, X_standardized: np.ndarray, Y_normalized: np.ndarray):
        x = _matrix(X_standardized, "standardized_geometry", 6)
        y = _matrix(Y_normalized, "normalized_target", MODEL_OUTPUTS)
        if len(x) != len(y):
            raise ValueError("krr_training_geometry_target_count_mismatch")
        self._c = KernelRidge(alpha=self.ridge_alpha, kernel="rbf", gamma=self.gamma).fit(
            x, y[:, :C_HAT_REAL_OUTPUTS])
        self._p = KernelRidge(alpha=self.ridge_alpha, kernel="rbf", gamma=self.gamma).fit(
            x, y[:, C_HAT_REAL_OUTPUTS:])
        return self

    def predict(self, X_standardized: np.ndarray) -> np.ndarray:
        if self._c is None or self._p is None:
            raise RuntimeError("krr_not_fitted")
        x = _matrix(X_standardized, "standardized_geometry", 6)
        y = np.concatenate((self._c.predict(x), self._p.predict(x)), axis=1)
        if y.shape != (len(x), MODEL_OUTPUTS) or not np.isfinite(y).all():
            raise ValueError("krr_prediction_invalid")
        return np.asarray(y, dtype=np.float64)

    def to_dict(self) -> Dict[str, Any]:
        return {"model": "RBF_KRR", "gamma": self.gamma, "ridge_alpha": self.ridge_alpha}


def krr_grid():
    return tuple((g, a) for g in KRR_GAMMAS for a in KRR_RIDGE_ALPHAS)


def mlp_parameter_count() -> int:
    w = MLP_HIDDEN_WIDTH
    return (6*w+w) + (w*w+w) + (w*C_HAT_REAL_OUTPUTS+C_HAT_REAL_OUTPUTS) + (w*21+21)


try:
    import torch
    from torch import nn
except ImportError as exc:  # pragma: no cover
    torch = None
    nn = None
    _TORCH_IMPORT_ERROR = exc
else:
    _TORCH_IMPORT_ERROR = None


if nn is not None:
    class CartesianMLP(nn.Module):
        """Shared 6->32 GELU->32 GELU trunk, separate 588 C / 21 log-P heads."""
        def __init__(self, seed: int):
            super().__init__()
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(int(seed))
                self.fc1 = nn.Linear(6, MLP_HIDDEN_WIDTH)
                self.fc2 = nn.Linear(MLP_HIDDEN_WIDTH, MLP_HIDDEN_WIDTH)
                self.c_hat_head = nn.Linear(MLP_HIDDEN_WIDTH, C_HAT_REAL_OUTPUTS)
                self.log_p_scale_head = nn.Linear(MLP_HIDDEN_WIDTH, 21)
            self.activation = nn.GELU()
            if self.parameter_count() != EXPECTED_MLP_PARAMETERS:
                raise RuntimeError("frozen_mlp_parameter_count_mismatch")

        def forward(self, X):
            h = self.activation(self.fc1(X))
            h = self.activation(self.fc2(h))
            return torch.cat((self.c_hat_head(h), self.log_p_scale_head(h)), dim=-1)

        def parameter_count(self) -> int:
            return sum(p.numel() for p in self.parameters())
else:
    class CartesianMLP:  # pragma: no cover
        def __init__(self, seed: int):
            raise RuntimeError("PyTorch_required_for_CartesianMLP") from _TORCH_IMPORT_ERROR


def mlp_loss_components(prediction_normalized, target_normalized):
    if torch is None:
        raise RuntimeError("PyTorch_required_for_CartesianMLP") from _TORCH_IMPORT_ERROR
    if prediction_normalized.shape != target_normalized.shape:
        raise ValueError("normalized_loss_shape_mismatch")
    if prediction_normalized.ndim != 2 or prediction_normalized.shape[1] != MODEL_OUTPUTS:
        raise ValueError("normalized_prediction_must_be_Nx609")
    lc = torch.mean(torch.square(prediction_normalized[:, :C_HAT_REAL_OUTPUTS] -
                                 target_normalized[:, :C_HAT_REAL_OUTPUTS]))
    lp = torch.mean(torch.square(prediction_normalized[:, C_HAT_REAL_OUTPUTS:] -
                                 target_normalized[:, C_HAT_REAL_OUTPUTS:]))
    return lc, lp, lc + lp


def numpy_loss_components(pred: np.ndarray, truth: np.ndarray):
    p = _matrix(pred, "normalized_prediction", MODEL_OUTPUTS)
    y = _matrix(truth, "normalized_target", MODEL_OUTPUTS)
    if p.shape != y.shape:
        raise ValueError("normalized_loss_shape_mismatch")
    lc = float(np.mean(np.square(p[:, :C_HAT_REAL_OUTPUTS] - y[:, :C_HAT_REAL_OUTPUTS])))
    lp = float(np.mean(np.square(p[:, C_HAT_REAL_OUTPUTS:] - y[:, C_HAT_REAL_OUTPUTS:])))
    return lc, lp, lc + lp
