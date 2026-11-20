"""
Scoring module for UdyamCred: Use trained models to score shops.

Provides:
1. ScorecardScorer: Predicts default probability and risk band
2. CapacityScorer: Predicts safe repayment amount
3. ModelEnsemble: Combined scoring pipeline
"""

import pickle
import json
import numpy as np
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScorecardResult:
    """Result from credibility scorecard."""
    default_probability: float  # 0-1
    risk_band: str  # 'Low', 'Moderate', 'High'
    confidence: float  # 0-1
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'default_probability': round(self.default_probability, 4),
            'risk_band': self.risk_band,
            'confidence': round(self.confidence, 4)
        }


@dataclass
class CapacityResult:
    """Result from repayment capacity model."""
    predicted_safe_emi: float  # ₹/month
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'predicted_safe_emi': round(self.predicted_safe_emi, 0)
        }


@dataclass
class ScoringResult:
    """Combined scoring result."""
    scorecard: ScorecardResult
    capacity: CapacityResult
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'scorecard': self.scorecard.to_dict(),
            'capacity': self.capacity.to_dict()
        }


class ScorecardScorer:
    """Score default probability using trained logistic regression."""
    
    # Risk band thresholds (default probability)
    THRESHOLDS = {
        'Low': 0.08,        # Default prob < 8% → Low risk
        'Moderate': 0.20,   # 8% ≤ prob < 20% → Moderate risk
        'High': float('inf')  # ≥ 20% → High risk
    }
    
    def __init__(self, model_path: str, scaler_path: str):
        """
        Initialize scorecard scorer.
        
        Args:
            model_path: Path to pickled logistic regression model
            scaler_path: Path to pickled StandardScaler
        """
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
        
        logger.info(f"Loaded scorecard model from {model_path}")
        logger.info(f"Loaded scaler from {scaler_path}")
    
    def score(self, features: np.ndarray) -> ScorecardResult:
        """
        Score a single shop or batch.
        
        Args:
            features: Feature vector(s), shape (n_features,) or (n_samples, n_features)
            
        Returns:
            ScorecardResult (or list of results if batch)
        """
        # Ensure 2D
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
            single = True
        else:
            single = False
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict probabilities
        proba = self.model.predict_proba(features_scaled)  # [[P(y=0), P(y=1)], ...]
        default_probs = proba[:, 1]  # P(default=1)
        
        # Map to risk bands
        if single:
            return self._make_result(default_probs[0])
        else:
            return [self._make_result(p) for p in default_probs]
    
    def _make_result(self, default_prob: float) -> ScorecardResult:
        """Create ScorecardResult from default probability."""
        # Determine risk band
        risk_band = 'High'
        for band, threshold in self.THRESHOLDS.items():
            if default_prob < threshold:
                risk_band = band
                break
        
        # Confidence: how far from the threshold?
        # Shops near band boundaries have lower confidence
        if risk_band == 'Low':
            threshold = self.THRESHOLDS['Low']
            distance = threshold - default_prob
            max_distance = threshold
        elif risk_band == 'Moderate':
            low_threshold = self.THRESHOLDS['Low']
            high_threshold = self.THRESHOLDS['Moderate']
            distance = min(default_prob - low_threshold, high_threshold - default_prob)
            max_distance = (high_threshold - low_threshold) / 2
        else:  # High
            threshold = self.THRESHOLDS['Moderate']
            distance = default_prob - threshold
            max_distance = 1.0 - threshold
        
        confidence = min(distance / max_distance, 1.0)
        
        return ScorecardResult(
            default_probability=default_prob,
            risk_band=risk_band,
            confidence=confidence
        )


class CapacityScorer:
    """Score repayment capacity (safe EMI) using trained regression model."""
    
    def __init__(self, model_path: str, scaler_path: str):
        """
        Initialize capacity scorer.
        
        Args:
            model_path: Path to pickled linear regression model
            scaler_path: Path to pickled StandardScaler
        """
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
        
        logger.info(f"Loaded capacity model from {model_path}")
        logger.info(f"Loaded scaler from {scaler_path}")
    
    def score(self, features: np.ndarray, min_emi: float = 1000, max_emi: float = 100000) -> CapacityResult:
        """
        Score safe repayment capacity.
        
        Args:
            features: Feature vector(s)
            min_emi: Minimum EMI bound (₹)
            max_emi: Maximum EMI bound (₹)
            
        Returns:
            CapacityResult (or list if batch)
        """
        # Ensure 2D
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
            single = True
        else:
            single = False
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict EMI
        emi_predictions = self.model.predict(features_scaled)
        
        # Apply bounds
        emi_predictions = np.clip(emi_predictions, min_emi, max_emi)
        
        if single:
            return CapacityResult(predicted_safe_emi=float(emi_predictions[0]))
        else:
            return [CapacityResult(predicted_safe_emi=float(emi)) for emi in emi_predictions]
    
    def score_batch(self, features: pd.DataFrame, feature_names: list,
                   min_emi: float = 1000, max_emi: float = 100000) -> np.ndarray:
        """
        Score a batch of shops from DataFrame.
        
        Args:
            features: DataFrame with features
            feature_names: List of feature column names (for alignment)
            min_emi: Minimum EMI
            max_emi: Maximum EMI
            
        Returns:
            Array of predicted EMIs
        """
        # Align features
        X = features[feature_names].fillna(features[feature_names].median())
        
        # Scale
        X_scaled = self.scaler.transform(X.values)
        
        # Predict
        predictions = self.model.predict(X_scaled)
        
        # Apply bounds
        return np.clip(predictions, min_emi, max_emi)


class ModelEnsemble:
    """Load and use all trained models."""
    
    def __init__(self, models_dir: str = 'ml/models'):
        """
        Initialize ensemble with all trained models.
        
        Args:
            models_dir: Directory containing model files
        """
        models_path = Path(models_dir)
        
        # Load metadata
        metadata_file = models_path / 'metadata.json'
        with open(metadata_file, 'r') as f:
            self.metadata = json.load(f)
        
        self.feature_names = self.metadata['features']
        
        # Load scorers
        self.scorecard = ScorecardScorer(
            str(models_path / 'scorecard.pkl'),
            str(models_path / 'scaler_scorecard.pkl')
        )
        
        self.capacity = CapacityScorer(
            str(models_path / 'capacity_model.pkl'),
            str(models_path / 'scaler_capacity.pkl')
        )
        
        logger.info(f"Loaded model ensemble from {models_dir}")
        logger.info(f"Features: {len(self.feature_names)}")
    
    def score_shop(self, features: Dict[str, float]) -> ScoringResult:
        """
        Score a single shop given features.
        
        Args:
            features: Dictionary of {feature_name: value}
            
        Returns:
            ScoringResult with both scorecard and capacity scores
        """
        # Build feature vector
        X = np.array([features.get(name, 0) for name in self.feature_names])
        
        # Score
        scorecard_result = self.scorecard.score(X)
        capacity_result = self.capacity.score(X)
        
        return ScoringResult(
            scorecard=scorecard_result,
            capacity=capacity_result
        )
    
    def score_batch(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Score a batch of shops.
        
        Args:
            features_df: DataFrame with rows as shops, columns as features
            
        Returns:
            DataFrame with scoring results
        """
        # Align features
        X = features_df[self.feature_names].fillna(
            features_df[self.feature_names].median()
        ).values
        
        # Score
        scorecard_results = self.scorecard.score(X)
        capacity_results = self.capacity.score(X)
        
        # Build results DataFrame
        results = pd.DataFrame({
            'default_probability': [r.default_probability for r in scorecard_results],
            'risk_band': [r.risk_band for r in scorecard_results],
            'scorecard_confidence': [r.confidence for r in scorecard_results],
            'safe_emi': [r.predicted_safe_emi for r in capacity_results]
        })
        
        return results
    
    def get_metrics(self) -> Dict:
        """Return training metrics."""
        return self.metadata.get('metrics', {})
    
    def get_feature_names(self) -> list:
        """Return feature names used for training."""
        return self.feature_names.copy()


def load_ensemble(models_dir: str = 'ml/models') -> ModelEnsemble:
    """Convenience function to load model ensemble."""
    return ModelEnsemble(models_dir)
