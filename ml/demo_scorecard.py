"""
Demo: Use trained Credibility Scorecard and Capacity Model to score shops.

This script:
1. Trains models (if not already trained)
2. Loads trained models
3. Scores a batch of shops from test set
4. Shows sample results
"""

import pandas as pd
import logging
import sys
from pathlib import Path

# Add ml to path
sys.path.insert(0, str(Path(__file__).parent))

from train_models import ModelTrainer
from scorer import load_ensemble

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def train_models_if_needed(models_dir: str = 'models') -> bool:
    """Check if models exist, train if not."""
    models_path = Path(models_dir)
    required_files = [
        'scorecard.pkl',
        'capacity_model.pkl',
        'metadata.json'
    ]
    
    if all((models_path / f).exists() for f in required_files):
        logger.info("✓ Models already trained")
        return False
    
    logger.info("Models not found. Training...")
    trainer = ModelTrainer(
        data_dir='ml/data',
        models_dir='models'
    )
    trainer.train_and_evaluate()
    return True


def demo_scoring():
    """Demonstrate scoring with trained models."""
    
    logger.info("\n" + "="*70)
    logger.info("UDYAMCRED: SCORECARD & CAPACITY MODEL DEMO")
    logger.info("="*70)
    
    # Train models if needed
    train_models_if_needed()
    
    # Load trained models
    logger.info("\nLoading trained models...")
    ensemble = load_ensemble('models')
    
    # Load test data
    logger.info("Loading test data (Generator 2)...")
    test_features = pd.read_csv('ml/data/features_gen2.csv')
    test_labels = pd.read_csv('ml/data/labels_gen2.csv')
    test_shops = pd.read_csv('ml/data/shops_gen2.csv')
    
    logger.info(f"Test set: {len(test_features)} shops")
    
    # Score batch
    logger.info("\nScoring shops...")
    results = ensemble.score_batch(test_features)
    
    # Merge with labels and shops for analysis
    results['shop_id'] = test_features['shop_id'].values
    results['actual_default'] = test_labels['default_6m'].values
    results['actual_safe_emi'] = test_labels['safe_emi_true'].values
    results['hidden_health'] = test_labels['hidden_health'].values
    results['shop_type'] = test_shops['shop_type'].values
    
    # ===== ANALYSIS =====
    
    logger.info("\n" + "="*70)
    logger.info("SCORING RESULTS SUMMARY")
    logger.info("="*70)
    
    # Risk band distribution
    logger.info("\n📊 RISK BAND DISTRIBUTION")
    risk_dist = results['risk_band'].value_counts()
    for band in ['Low', 'Moderate', 'High']:
        count = risk_dist.get(band, 0)
        pct = 100 * count / len(results)
        logger.info(f"  {band:10s}: {count:4d} shops ({pct:5.1f}%)")
    
    # Default rate by risk band
    logger.info("\n🎯 ACTUAL DEFAULT RATE BY RISK BAND")
    for band in ['Low', 'Moderate', 'High']:
        mask = results['risk_band'] == band
        if mask.sum() == 0:
            continue
        default_rate = results[mask]['actual_default'].mean()
        count = mask.sum()
        logger.info(f"  {band:10s}: {default_rate:6.1%} default rate ({count} shops)")
    
    # EMI prediction accuracy
    logger.info("\n💰 EMI PREDICTION ACCURACY")
    results['emi_error'] = abs(results['safe_emi'] - results['actual_safe_emi'])
    results['emi_error_pct'] = 100 * results['emi_error'] / results['actual_safe_emi']
    
    mae = results['emi_error'].mean()
    median_error_pct = results['emi_error_pct'].median()
    logger.info(f"  Mean Absolute Error: ₹{mae:,.0f}")
    logger.info(f"  Median % Error: {median_error_pct:.1f}%")
    
    # Sample predictions
    logger.info("\n" + "="*70)
    logger.info("SAMPLE PREDICTIONS (5 shops)")
    logger.info("="*70)
    
    sample_results = results.head(5)[
        ['shop_id', 'risk_band', 'default_probability', 'scorecard_confidence',
         'safe_emi', 'actual_default', 'actual_safe_emi', 'hidden_health', 'shop_type']
    ].copy()
    
    for idx, row in sample_results.iterrows():
        logger.info(f"\n  Shop: {row['shop_id']}")
        logger.info(f"    Type: {row['shop_type']}, Hidden Health: {row['hidden_health']}")
        logger.info(f"    Scorecard: {row['risk_band']:10s} (P(default)={row['default_probability']:.1%}, conf={row['scorecard_confidence']:.2f})")
        logger.info(f"    Predicted EMI: ₹{row['safe_emi']:,.0f} (actual: ₹{row['actual_safe_emi']:,.0f})")
        logger.info(f"    Actual default: {bool(row['actual_default'])}")
    
    # Calibration check: for each risk band, is predicted default prob close to actual?
    logger.info("\n" + "="*70)
    logger.info("SCORECARD CALIBRATION CHECK")
    logger.info("="*70)
    logger.info("\nPredicted vs Actual Default Rate by Risk Band:")
    
    for band in ['Low', 'Moderate', 'High']:
        mask = results['risk_band'] == band
        if mask.sum() == 0:
            continue
        
        band_results = results[mask]
        predicted_prob = band_results['default_probability'].mean()
        actual_rate = band_results['actual_default'].mean()
        count = mask.sum()
        
        logger.info(f"  {band:10s}: predicted={predicted_prob:6.1%}, actual={actual_rate:6.1%} ({count} shops)")
    
    # Shop type analysis
    logger.info("\n" + "="*70)
    logger.info("DEFAULT RATE BY SHOP TYPE")
    logger.info("="*70)
    
    for shop_type in results['shop_type'].unique():
        mask = results['shop_type'] == shop_type
        default_rate = results[mask]['actual_default'].mean()
        count = mask.sum()
        avg_risk_band = results[mask]['risk_band'].value_counts().index[0]
        logger.info(f"  {shop_type:20s}: {default_rate:6.1%} default ({count:3d} shops, avg={avg_risk_band})")
    
    # Health-based analysis
    logger.info("\n" + "="*70)
    logger.info("DEFAULT RATE BY HIDDEN HEALTH")
    logger.info("="*70)
    
    for health in sorted(results['hidden_health'].unique()):
        mask = results['hidden_health'] == health
        default_rate = results[mask]['actual_default'].mean()
        count = mask.sum()
        avg_prob = results[mask]['default_probability'].mean()
        logger.info(f"  {health:12s}: {default_rate:6.1%} default ({count:3d} shops, avg prob={avg_prob:6.1%})")
    
    # Training metrics
    logger.info("\n" + "="*70)
    logger.info("TRAINING METRICS (from metadata)")
    logger.info("="*70)
    
    metrics = ensemble.get_metrics()
    
    if 'scorecard' in metrics:
        logger.info("\n📊 SCORECARD (Logistic Regression)")
        logger.info(f"  Train AUC: {metrics['scorecard'].get('train_auc', 'N/A'):.4f}")
        if 'val_auc' in metrics['scorecard']:
            logger.info(f"  Val AUC:   {metrics['scorecard']['val_auc']:.4f}")
    
    if 'capacity_model' in metrics:
        logger.info("\n💰 CAPACITY MODEL (Linear Regression)")
        logger.info(f"  Train R²: {metrics['capacity_model'].get('train_r2', 'N/A'):.4f}")
        logger.info(f"  Train MAE: ₹{metrics['capacity_model'].get('train_mae', 0):,.0f}")
        if 'val_r2' in metrics['capacity_model']:
            logger.info(f"  Val R²:   {metrics['capacity_model']['val_r2']:.4f}")
    
    if 'test' in metrics:
        logger.info("\n🧪 TEST SET (Generator 2)")
        if 'test_auc_scorecard' in metrics['test']:
            logger.info(f"  Scorecard AUC: {metrics['test']['test_auc_scorecard']:.4f}")
        if 'test_r2_capacity' in metrics['test']:
            logger.info(f"  Capacity R²: {metrics['test']['test_r2_capacity']:.4f}")
    
    logger.info("\n" + "="*70)
    logger.info("✓ DEMO COMPLETE")
    logger.info("="*70)


if __name__ == '__main__':
    demo_scoring()
