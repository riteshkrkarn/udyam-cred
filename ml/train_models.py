"""
Train UdyamCred ML models: Credibility Scorecard and Repayment Capacity Model.

Models:
1. Credibility Scorecard (Logistic Regression)
   - Predicts probability of default (0-1)
   - Outputs: default_probability, risk_band (Low/Moderate/High), confidence

2. Repayment Capacity Model (Linear Regression)
   - Predicts safe repayment amount (₹/month)
   - Bounded by business rules and policy caps
   - Outputs: safe_emi

Both models trained on Generator 1 (5,000 shops), tested on Generator 2 (1,500 shops).
"""

import pandas as pd
import numpy as np
import pickle
import json
import logging
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import (
    roc_auc_score, roc_curve, precision_recall_curve, 
    mean_absolute_error, mean_squared_error, r2_score
)
from typing import Tuple, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """Train and evaluate ML models for UdyamCred."""
    
    def __init__(self, data_dir: str = 'ml/ml/data', models_dir: str = 'ml/models'):
        """
        Initialize trainer.
        
        Args:
            data_dir: Path to generated datasets
            models_dir: Path to save trained models
        """
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.scaler_scorecard = StandardScaler()
        self.scaler_capacity = StandardScaler()
        
        logger.info(f"Initialized ModelTrainer. Models dir: {self.models_dir}")
    
    def load_data(self, gen_id: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load features, labels, and shops for a generator.
        
        Args:
            gen_id: Generator ID (1 or 2)
            
        Returns:
            Tuple of (features_df, labels_df, shops_df)
        """
        features_file = self.data_dir / f'features_gen{gen_id}.csv'
        labels_file = self.data_dir / f'labels_gen{gen_id}.csv'
        shops_file = self.data_dir / f'shops_gen{gen_id}.csv'
        
        logger.info(f"Loading Generator {gen_id} data...")
        features = pd.read_csv(features_file)
        labels = pd.read_csv(labels_file)
        shops = pd.read_csv(shops_file)
        
        logger.info(f"  Features: {features.shape}")
        logger.info(f"  Labels: {labels.shape}")
        logger.info(f"  Shops: {shops.shape}")
        
        return features, labels, shops
    
    def prepare_features(self, features: pd.DataFrame, exclude_cols: list = None) -> Tuple[pd.DataFrame, list]:
        """
        Prepare feature matrix for model training.
        
        Drops shop_id and flag columns, handles missing values.
        
        Args:
            features: Raw feature dataframe
            exclude_cols: Additional columns to exclude
            
        Returns:
            Tuple of (prepared features, feature column names)
        """
        if exclude_cols is None:
            exclude_cols = []
        
        # Drop identifiers and flags
        exclude_cols = ['shop_id'] + exclude_cols
        cols_to_drop = [col for col in exclude_cols if col in features.columns]
        cols_to_drop += [col for col in features.columns if col.endswith('_flag')]
        
        X = features.drop(columns=cols_to_drop)
        
        # Handle missing values: fill with median
        X = X.fillna(X.median())
        
        feature_names = X.columns.tolist()
        logger.info(f"Prepared {len(feature_names)} features for training")
        
        return X, feature_names
    
    def train_scorecard(self, X_train: pd.DataFrame, y_train: np.ndarray,
                       X_val: pd.DataFrame = None, y_val: np.ndarray = None) -> Tuple[LogisticRegression, dict]:
        """
        Train credibility scorecard (logistic regression).
        
        Args:
            X_train: Training features
            y_train: Training labels (default_6m: 0 or 1)
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            
        Returns:
            Tuple of (trained model, metrics dict)
        """
        logger.info("\n" + "="*60)
        logger.info("TRAINING CREDIBILITY SCORECARD (Logistic Regression)")
        logger.info("="*60)
        
        # Standardize features
        X_train_scaled = self.scaler_scorecard.fit_transform(X_train)
        
        # Train logistic regression
        model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight='balanced'  # Handle class imbalance
        )
        model.fit(X_train_scaled, y_train)
        
        logger.info(f"Model trained. Classes: {model.classes_}")
        
        # Evaluate on training set
        y_pred_proba_train = model.predict_proba(X_train_scaled)[:, 1]
        train_auc = roc_auc_score(y_train, y_pred_proba_train)
        logger.info(f"Training AUC: {train_auc:.4f}")
        
        metrics = {
            'train_auc': float(train_auc),
            'train_default_rate': float(y_train.mean()),
            'train_samples': int(len(y_train))
        }
        
        # Evaluate on validation set if provided
        if X_val is not None and y_val is not None:
            X_val_scaled = self.scaler_scorecard.transform(X_val)
            y_pred_proba_val = model.predict_proba(X_val_scaled)[:, 1]
            val_auc = roc_auc_score(y_val, y_pred_proba_val)
            logger.info(f"Validation AUC: {val_auc:.4f}")
            metrics['val_auc'] = float(val_auc)
            metrics['val_default_rate'] = float(y_val.mean())
            metrics['val_samples'] = int(len(y_val))
        
        logger.info("✓ Scorecard training complete")
        
        return model, metrics
    
    def train_capacity_model(self, X_train: pd.DataFrame, y_train: np.ndarray,
                            X_val: pd.DataFrame = None, y_val: np.ndarray = None) -> Tuple[LinearRegression, dict]:
        """
        Train repayment capacity model (linear regression).
        
        Predicts safe_emi_true from features. Output is bounded by business rules.
        
        Args:
            X_train: Training features
            y_train: Training labels (safe_emi_true: ₹/month)
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            
        Returns:
            Tuple of (trained model, metrics dict)
        """
        logger.info("\n" + "="*60)
        logger.info("TRAINING REPAYMENT CAPACITY MODEL (Linear Regression)")
        logger.info("="*60)
        
        # Standardize features
        X_train_scaled = self.scaler_capacity.fit_transform(X_train)
        
        # Train linear regression
        model = LinearRegression()
        model.fit(X_train_scaled, y_train)
        
        logger.info("Model trained")
        
        # Evaluate on training set
        y_pred_train = model.predict(X_train_scaled)
        train_mae = mean_absolute_error(y_train, y_pred_train)
        train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
        train_r2 = r2_score(y_train, y_pred_train)
        
        logger.info(f"Training MAE: ₹{train_mae:.0f}")
        logger.info(f"Training RMSE: ₹{train_rmse:.0f}")
        logger.info(f"Training R²: {train_r2:.4f}")
        
        metrics = {
            'train_mae': float(train_mae),
            'train_rmse': float(train_rmse),
            'train_r2': float(train_r2),
            'train_mean_emi': float(y_train.mean()),
            'train_std_emi': float(y_train.std()),
            'train_samples': int(len(y_train))
        }
        
        # Evaluate on validation set if provided
        if X_val is not None and y_val is not None:
            X_val_scaled = self.scaler_capacity.transform(X_val)
            y_pred_val = model.predict(X_val_scaled)
            val_mae = mean_absolute_error(y_val, y_pred_val)
            val_rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
            val_r2 = r2_score(y_val, y_pred_val)
            
            logger.info(f"Validation MAE: ₹{val_mae:.0f}")
            logger.info(f"Validation RMSE: ₹{val_rmse:.0f}")
            logger.info(f"Validation R²: {val_r2:.4f}")
            
            metrics['val_mae'] = float(val_mae)
            metrics['val_rmse'] = float(val_rmse)
            metrics['val_r2'] = float(val_r2)
            metrics['val_mean_emi'] = float(y_val.mean())
            metrics['val_std_emi'] = float(y_val.std())
            metrics['val_samples'] = int(len(y_val))
        
        logger.info("✓ Capacity model training complete")
        
        return model, metrics
    
    def evaluate_on_test_set(self, scorecard: LogisticRegression, 
                             capacity_model: LinearRegression,
                             X_test: pd.DataFrame, features_names: list,
                             y_test_default: np.ndarray = None,
                             y_test_emi: np.ndarray = None) -> Dict[str, Any]:
        """
        Evaluate both models on test set (Generator 2).
        
        Args:
            scorecard: Trained scorecard model
            capacity_model: Trained capacity model
            X_test: Test features
            features_names: Feature column names (for alignment)
            y_test_default: Test default labels (optional)
            y_test_emi: Test EMI labels (optional)
            
        Returns:
            Dictionary of test metrics
        """
        logger.info("\n" + "="*60)
        logger.info("EVALUATING ON TEST SET (Generator 2)")
        logger.info("="*60)
        
        # Ensure features are aligned
        X_test_aligned = X_test[features_names].fillna(X_test[features_names].median())
        
        metrics = {}
        
        # Evaluate scorecard
        if y_test_default is not None:
            X_test_scaled = self.scaler_scorecard.transform(X_test_aligned)
            y_pred_proba = scorecard.predict_proba(X_test_scaled)[:, 1]
            test_auc = roc_auc_score(y_test_default, y_pred_proba)
            logger.info(f"Test AUC (Scorecard): {test_auc:.4f}")
            metrics['test_auc_scorecard'] = float(test_auc)
            metrics['test_default_rate'] = float(y_test_default.mean())
        
        # Evaluate capacity model
        if y_test_emi is not None:
            X_test_scaled = self.scaler_capacity.transform(X_test_aligned)
            y_pred_emi = capacity_model.predict(X_test_scaled)
            test_mae = mean_absolute_error(y_test_emi, y_pred_emi)
            test_rmse = np.sqrt(mean_squared_error(y_test_emi, y_pred_emi))
            test_r2 = r2_score(y_test_emi, y_pred_emi)
            
            logger.info(f"Test MAE (Capacity): ₹{test_mae:.0f}")
            logger.info(f"Test RMSE (Capacity): ₹{test_rmse:.0f}")
            logger.info(f"Test R² (Capacity): {test_r2:.4f}")
            
            metrics['test_mae_capacity'] = float(test_mae)
            metrics['test_rmse_capacity'] = float(test_rmse)
            metrics['test_r2_capacity'] = float(test_r2)
            metrics['test_mean_emi'] = float(y_test_emi.mean())
        
        logger.info("✓ Test evaluation complete")
        return metrics
    
    def save_models(self, scorecard: LogisticRegression, 
                   capacity_model: LinearRegression,
                   feature_names: list, all_metrics: dict) -> None:
        """
        Save trained models and metadata.
        
        Args:
            scorecard: Trained scorecard
            capacity_model: Trained capacity model
            feature_names: List of feature names
            all_metrics: All training metrics
        """
        logger.info("\n" + "="*60)
        logger.info("SAVING MODELS")
        logger.info("="*60)
        
        # Save models
        scorecard_path = self.models_dir / 'scorecard.pkl'
        capacity_path = self.models_dir / 'capacity_model.pkl'
        scaler_scorecard_path = self.models_dir / 'scaler_scorecard.pkl'
        scaler_capacity_path = self.models_dir / 'scaler_capacity.pkl'
        
        with open(scorecard_path, 'wb') as f:
            pickle.dump(scorecard, f)
        logger.info(f"✓ Saved: {scorecard_path}")
        
        with open(capacity_path, 'wb') as f:
            pickle.dump(capacity_model, f)
        logger.info(f"✓ Saved: {capacity_path}")
        
        with open(scaler_scorecard_path, 'wb') as f:
            pickle.dump(self.scaler_scorecard, f)
        logger.info(f"✓ Saved: {scaler_scorecard_path}")
        
        with open(scaler_capacity_path, 'wb') as f:
            pickle.dump(self.scaler_capacity, f)
        logger.info(f"✓ Saved: {scaler_capacity_path}")
        
        # Save metadata
        metadata = {
            'version': '1.0',
            'created_at': pd.Timestamp.now().isoformat(),
            'features': feature_names,
            'metrics': all_metrics,
            'scorecard_info': {
                'type': 'LogisticRegression',
                'classes': scorecard.classes_.tolist(),
                'coefficients_shape': scorecard.coef_.shape,
            },
            'capacity_model_info': {
                'type': 'LinearRegression',
                'coefficients_shape': capacity_model.coef_.shape,
            }
        }
        
        metadata_path = self.models_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✓ Saved: {metadata_path}")
        
        logger.info(f"\nAll models saved to: {self.models_dir}")
    
    def train_and_evaluate(self) -> None:
        """
        Main training pipeline:
        1. Load Generator 1 (training data)
        2. Train scorecard and capacity model
        3. Load Generator 2 (test data)
        4. Evaluate on test set
        5. Save all models
        """
        logger.info("\n" + "="*70)
        logger.info("UDYAMCRED: ML MODEL TRAINING PIPELINE")
        logger.info("="*70)
        
        # ===== Load training data (Generator 1) =====
        features_train, labels_train, shops_train = self.load_data(1)
        
        # Prepare features
        X_train, feature_names = self.prepare_features(features_train)
        y_train_default = labels_train['default_6m'].values
        y_train_emi = labels_train['safe_emi_true'].values
        
        # Split training data: 70% train, 30% validation
        train_size = int(0.7 * len(X_train))
        indices = np.random.RandomState(42).permutation(len(X_train))
        train_idx = indices[:train_size]
        val_idx = indices[train_size:]
        
        X_train_split = X_train.iloc[train_idx].reset_index(drop=True)
        y_train_split = y_train_default[train_idx]
        y_train_emi_split = y_train_emi[train_idx]
        
        X_val = X_train.iloc[val_idx].reset_index(drop=True)
        y_val = y_train_default[val_idx]
        y_val_emi = y_train_emi[val_idx]
        
        logger.info(f"\nTrain set: {len(X_train_split)} samples")
        logger.info(f"Validation set: {len(X_val)} samples")
        logger.info(f"Default rate (train): {y_train_split.mean():.2%}")
        logger.info(f"Default rate (val): {y_val.mean():.2%}")
        
        # ===== Train models =====
        scorecard, scorecard_metrics = self.train_scorecard(
            X_train_split, y_train_split, X_val, y_val
        )
        
        capacity_model, capacity_metrics = self.train_capacity_model(
            X_train_split, y_train_emi_split, X_val, y_val_emi
        )
        
        # ===== Load test data (Generator 2) =====
        features_test, labels_test, shops_test = self.load_data(2)
        X_test, _ = self.prepare_features(features_test)
        y_test_default = labels_test['default_6m'].values
        y_test_emi = labels_test['safe_emi_true'].values
        
        logger.info(f"\nTest set: {len(X_test)} samples")
        logger.info(f"Default rate (test): {y_test_default.mean():.2%}")
        
        # ===== Evaluate on test set =====
        test_metrics = self.evaluate_on_test_set(
            scorecard, capacity_model, X_test, feature_names,
            y_test_default, y_test_emi
        )
        
        # ===== Combine all metrics =====
        all_metrics = {
            'scorecard': scorecard_metrics,
            'capacity_model': capacity_metrics,
            'test': test_metrics
        }
        
        # ===== Save models =====
        self.save_models(scorecard, capacity_model, feature_names, all_metrics)
        
        logger.info("\n" + "="*70)
        logger.info("✓ TRAINING PIPELINE COMPLETE")
        logger.info("="*70)
        
        # Print summary
        self._print_summary(all_metrics)
    
    def _print_summary(self, metrics: Dict[str, Any]) -> None:
        """Print training summary."""
        logger.info("\n" + "="*70)
        logger.info("TRAINING SUMMARY")
        logger.info("="*70)
        
        logger.info("\n📊 SCORECARD (Logistic Regression)")
        logger.info(f"  Train AUC: {metrics['scorecard']['train_auc']:.4f}")
        if 'val_auc' in metrics['scorecard']:
            logger.info(f"  Val AUC:   {metrics['scorecard']['val_auc']:.4f}")
        if 'test' in metrics and 'test_auc_scorecard' in metrics['test']:
            logger.info(f"  Test AUC:  {metrics['test']['test_auc_scorecard']:.4f}")
        
        logger.info("\n💰 CAPACITY MODEL (Linear Regression)")
        logger.info(f"  Train R²:  {metrics['capacity_model']['train_r2']:.4f}")
        logger.info(f"  Train MAE: ₹{metrics['capacity_model']['train_mae']:.0f}")
        if 'val_r2' in metrics['capacity_model']:
            logger.info(f"  Val R²:    {metrics['capacity_model']['val_r2']:.4f}")
            logger.info(f"  Val MAE:   ₹{metrics['capacity_model']['val_mae']:.0f}")
        if 'test' in metrics and 'test_r2_capacity' in metrics['test']:
            logger.info(f"  Test R²:   {metrics['test']['test_r2_capacity']:.4f}")
            logger.info(f"  Test MAE:  ₹{metrics['test']['test_mae_capacity']:.0f}")
        
        logger.info("\n" + "="*70)


def main():
    """Run the training pipeline."""
    trainer = ModelTrainer(
        data_dir='ml/data',
        models_dir='models'
    )
    trainer.train_and_evaluate()


if __name__ == '__main__':
    main()
