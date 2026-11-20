# ML Model Training Guide

Complete walkthrough for training the UdyamCred credit scoring models.

## Overview

This guide covers training two core models:

1. **Credibility Scorecard** (Logistic Regression)
   - Predicts credit risk (default probability)
   - Explainable, with sign-constrained features
   - Output: Risk band (Low, Moderate, High, Needs Review) + confidence

2. **Repayment Capacity Model** (Regression with Bounds)
   - Predicts safe monthly repayment amount
   - Bounded by policy caps and stock limits
   - Output: Safe EMI (cannot exceed hard limits)

## Prerequisites

```bash
cd ml
pip install scikit-learn scipy pandas numpy
```

## Step 1: Load and Prepare Data

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score, mean_absolute_error, mean_squared_error

# Load data
features_gen1 = pd.read_csv('ml/data/features_gen1.csv')
labels_gen1 = pd.read_csv('ml/data/labels_gen1.csv')
features_gen2 = pd.read_csv('ml/data/features_gen2.csv')
labels_gen2 = pd.read_csv('ml/data/labels_gen2.csv')

# Merge features and labels
train_data = features_gen1.merge(labels_gen1, on='shop_id')
test_data = features_gen2.merge(labels_gen2, on='shop_id')

print(f"Training set: {len(train_data)} shops")
print(f"Test set: {len(test_data)} shops")
print(f"Default rate (train): {train_data['default_6m'].mean():.1%}")
print(f"Default rate (test): {test_data['default_6m'].mean():.1%}")
```

## Step 2: Select Features

```python
# Select feature columns (exclude ID, labels, and flags)
exclude_cols = {'shop_id', 'default_6m', 'safe_emi_true', 'hidden_health'}
flag_cols = [c for c in features_gen1.columns if '_flag' in c]
feature_cols = [c for c in features_gen1.columns 
                if c not in exclude_cols and c not in flag_cols]

print(f"Selected {len(feature_cols)} features:")
print(feature_cols[:10])  # Show first 10

# Prepare feature matrices
X_train = train_data[feature_cols].fillna(0)
y_train_default = train_data['default_6m'].values
y_train_emi = train_data['safe_emi_true'].values

X_test = test_data[feature_cols].fillna(0)
y_test_default = test_data['default_6m'].values
y_test_emi = test_data['safe_emi_true'].values

# Standardize features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"\nFeature matrix: {X_train_scaled.shape}")
```

## Step 3: Train Scorecard (Default Model)

```python
# Train logistic regression for default prediction
scorecard = LogisticRegression(
    max_iter=1000,
    random_state=42,
    class_weight='balanced'  # Handle class imbalance
)

scorecard.fit(X_train_scaled, y_train_default)

# Predictions
y_train_pred_proba = scorecard.predict_proba(X_train_scaled)[:, 1]
y_test_pred_proba = scorecard.predict_proba(X_test_scaled)[:, 1]

# Evaluation
train_auc = roc_auc_score(y_train_default, y_train_pred_proba)
test_auc = roc_auc_score(y_test_default, y_test_pred_proba)

print("=" * 60)
print("SCORECARD PERFORMANCE (Default Prediction)")
print("=" * 60)
print(f"Train AUC-ROC: {train_auc:.4f}")
print(f"Test AUC-ROC:  {test_auc:.4f}")
print(f"\nTrain accuracy: {scorecard.score(X_train_scaled, y_train_default):.4f}")
print(f"Test accuracy:  {scorecard.score(X_test_scaled, y_test_default):.4f}")

# Feature importance (coefficients)
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'coefficient': scorecard.coef_[0],
    'abs_coefficient': np.abs(scorecard.coef_[0])
}).sort_values('abs_coefficient', ascending=False)

print("\nTop 10 Most Important Features:")
print(feature_importance.head(10)[['feature', 'coefficient']])
```

## Step 4: Define Risk Bands

```python
def get_risk_band(default_prob, confidence):
    """Map default probability to risk band."""
    if default_prob < 0.05:
        return 'Low'
    elif default_prob < 0.12:
        return 'Moderate'
    elif default_prob < 0.20:
        return 'High'
    else:
        return 'Needs Review'

def get_confidence(data_quality_flags):
    """
    Calculate confidence based on data availability.
    Higher = more confident (more data sources agree)
    """
    n_flags = data_quality_flags.sum()  # Count missing data flags
    confidence = max(0.5, 1.0 - (n_flags * 0.1))
    return confidence

# Apply risk bands to test set
test_data['default_probability'] = y_test_pred_proba
test_data['risk_band'] = test_data['default_probability'].apply(
    lambda p: get_risk_band(p, 0.8)
)

# Calculate confidence for each shop
flag_cols_in_test = [c for c in test_data.columns if '_flag' in c]
test_data['data_quality_flags'] = test_data[flag_cols_in_test].sum(axis=1)
test_data['confidence'] = test_data['data_quality_flags'].apply(
    lambda flags: get_confidence(pd.Series([flags]))
)

print("\nRisk Band Distribution (Test Set):")
print(test_data['risk_band'].value_counts())
print(f"\nAverage confidence: {test_data['confidence'].mean():.2f}")
```

## Step 5: Train Capacity Model (EMI Prediction)

```python
# Train regression model for safe EMI prediction
capacity_model = Ridge(alpha=1.0, random_state=42)
capacity_model.fit(X_train_scaled, y_train_emi)

# Predictions
y_train_emi_pred = capacity_model.predict(X_train_scaled)
y_test_emi_pred = capacity_model.predict(X_test_scaled)

# Ensure predictions don't exceed limits
STOCK_LIMIT = 50000  # Max stock-based limit
POLICY_CAP = 100000  # Max policy limit

y_train_emi_pred = np.minimum(y_train_emi_pred, STOCK_LIMIT)
y_train_emi_pred = np.minimum(y_train_emi_pred, POLICY_CAP)

y_test_emi_pred = np.minimum(y_test_emi_pred, STOCK_LIMIT)
y_test_emi_pred = np.minimum(y_test_emi_pred, POLICY_CAP)

# Evaluation
train_mae = mean_absolute_error(y_train_emi, y_train_emi_pred)
test_mae = mean_absolute_error(y_test_emi, y_test_emi_pred)
train_rmse = np.sqrt(mean_squared_error(y_train_emi, y_train_emi_pred))
test_rmse = np.sqrt(mean_squared_error(y_test_emi, y_test_emi_pred))

print("=" * 60)
print("CAPACITY MODEL PERFORMANCE (Safe EMI Prediction)")
print("=" * 60)
print(f"Train MAE:  Rs {train_mae:,.0f}")
print(f"Test MAE:   Rs {test_mae:,.0f}")
print(f"Train RMSE: Rs {train_rmse:,.0f}")
print(f"Test RMSE:  Rs {test_rmse:,.0f}")

# Verify bounds
print(f"\nBound Verification (Test):")
print(f"  Min predicted EMI: Rs {y_test_emi_pred.min():,.0f}")
print(f"  Max predicted EMI: Rs {y_test_emi_pred.max():,.0f}")
print(f"  All within limits: {(y_test_emi_pred <= POLICY_CAP).all()}")
```

## Step 6: Reason Code Generation

```python
def get_reason_codes(shop_features, coefficients, feature_cols, top_n=3):
    """
    Extract top N contributing features as reason codes.
    """
    contributions = np.abs(shop_features.values * coefficients)
    top_indices = np.argsort(contributions)[-top_n:][::-1]
    
    reasons = []
    for idx in top_indices:
        feature = feature_cols[idx]
        coef = coefficients[idx]
        value = shop_features.values[idx]
        
        direction = "increases" if coef > 0 else "decreases"
        reasons.append(f"{feature} {direction} risk")
    
    return reasons

# Generate reason codes for first 5 test shops
print("\nSample Reason Codes:")
print("=" * 60)
for i in range(min(5, len(test_data))):
    shop_row = test_data.iloc[i]
    shop_features = X_test.iloc[i]
    
    reasons = get_reason_codes(
        shop_features, 
        scorecard.coef_[0], 
        feature_cols,
        top_n=3
    )
    
    print(f"\nShop {i+1} (Risk: {shop_row['risk_band']}):")
    for reason in reasons:
        print(f"  • {reason}")
```

## Step 7: Fairness Audit

```python
# Compare outcomes with and without family_size
test_data['family_size_group'] = pd.cut(
    test_data['family_size'],
    bins=[0, 2, 4, 10],
    labels=['Small (1-2)', 'Medium (3-4)', 'Large (5+)']
)

print("\nFairness Audit: Default Rate by Family Size")
print("=" * 60)
fairness = test_data.groupby('family_size_group').agg({
    'default_6m': 'mean',
    'default_probability': 'mean',
    'safe_emi_true': 'mean',
    'shop_id': 'count'
}).rename(columns={'shop_id': 'count'})

print(fairness)

# Check for disparate impact
print("\nChecking for disparate impact...")
small_family_default = fairness.loc['Small (1-2)', 'default_6m']
large_family_default = fairness.loc['Large (5+)', 'default_6m']
ratio = small_family_default / large_family_default

print(f"Small family default rate: {small_family_default:.1%}")
print(f"Large family default rate: {large_family_default:.1%}")
print(f"Ratio: {ratio:.2f}")
if ratio > 1.25 or ratio < 0.8:
    print("⚠️  Potential disparate impact detected")
else:
    print("✓ No significant disparate impact")
```

## Step 8: Baseline Comparison

```python
from sklearn.linear_model import LogisticRegression

# UPI-only baseline
upi_features = ['avg_upi_inflow', 'std_upi_inflow', 'total_upi_inflow']
upi_features_present = [f for f in upi_features if f in feature_cols]

if upi_features_present:
    upi_baseline = LogisticRegression(max_iter=1000)
    upi_baseline.fit(X_train_scaled[:, [feature_cols.index(f) for f in upi_features_present]], 
                     y_train_default)
    
    upi_auc = roc_auc_score(
        y_test_default,
        upi_baseline.predict_proba(
            X_test_scaled[:, [feature_cols.index(f) for f in upi_features_present]]
        )[:, 1]
    )
    
    print("\nBASELINE COMPARISON")
    print("=" * 60)
    print(f"UPI-only baseline AUC: {upi_auc:.4f}")
    print(f"Scorecard AUC:         {test_auc:.4f}")
    print(f"Improvement:           +{(test_auc - upi_auc):.4f}")
```

## Step 9: Save Models

```python
import pickle
from pathlib import Path

# Create models directory
models_dir = Path('ml/models')
models_dir.mkdir(exist_ok=True)

# Save scorecard
with open(models_dir / 'scorecard.pkl', 'wb') as f:
    pickle.dump(scorecard, f)

# Save capacity model
with open(models_dir / 'capacity_model.pkl', 'wb') as f:
    pickle.dump(capacity_model, f)

# Save scaler
with open(models_dir / 'scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

# Save feature columns
with open(models_dir / 'feature_columns.pkl', 'wb') as f:
    pickle.dump(feature_cols, f)

# Save configuration
config = {
    'stock_limit': STOCK_LIMIT,
    'policy_cap': POLICY_CAP,
    'feature_count': len(feature_cols),
    'scorecard_auc': test_auc,
    'capacity_mae': test_mae,
    'training_date': pd.Timestamp.now().isoformat()
}

import json
with open(models_dir / 'config.json', 'w') as f:
    json.dump(config, f, indent=2)

print(f"✓ Models saved to {models_dir}")
```

## Step 10: Load and Use Trained Models

```python
import pickle

models_dir = Path('ml/models')

# Load models
with open(models_dir / 'scorecard.pkl', 'rb') as f:
    scorecard_loaded = pickle.load(f)

with open(models_dir / 'capacity_model.pkl', 'rb') as f:
    capacity_loaded = pickle.load(f)

with open(models_dir / 'scaler.pkl', 'rb') as f:
    scaler_loaded = pickle.load(f)

with open(models_dir / 'feature_columns.pkl', 'rb') as f:
    feature_cols_loaded = pickle.load(f)

# Make predictions on new shop
new_shop_features = X_test.iloc[0:1]  # Take first test shop as example
new_shop_features_scaled = scaler_loaded.transform(new_shop_features)

default_prob = scorecard_loaded.predict_proba(new_shop_features_scaled)[0, 1]
safe_emi = capacity_loaded.predict(new_shop_features_scaled)[0]

print(f"Prediction for new shop:")
print(f"  Default probability: {default_prob:.2%}")
print(f"  Safe EMI: Rs {safe_emi:,.0f}")
```

## Complete Training Script

Save as `ml/train_models.py`:

```python
#!/usr/bin/env python3
"""
Train UdyamCred scorecard and capacity models.

Usage:
    python train_models.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, mean_absolute_error, mean_squared_error
import pickle
import json

def main():
    # Load data
    print("Loading data...")
    features_gen1 = pd.read_csv('ml/data/features_gen1.csv')
    labels_gen1 = pd.read_csv('ml/data/labels_gen1.csv')
    features_gen2 = pd.read_csv('ml/data/features_gen2.csv')
    labels_gen2 = pd.read_csv('ml/data/labels_gen2.csv')
    
    train_data = features_gen1.merge(labels_gen1, on='shop_id')
    test_data = features_gen2.merge(labels_gen2, on='shop_id')
    
    # Select features
    exclude_cols = {'shop_id', 'default_6m', 'safe_emi_true', 'hidden_health'}
    flag_cols = [c for c in features_gen1.columns if '_flag' in c]
    feature_cols = [c for c in features_gen1.columns 
                    if c not in exclude_cols and c not in flag_cols]
    
    X_train = train_data[feature_cols].fillna(0)
    y_train_default = train_data['default_6m'].values
    y_train_emi = train_data['safe_emi_true'].values
    
    X_test = test_data[feature_cols].fillna(0)
    y_test_default = test_data['default_6m'].values
    y_test_emi = test_data['safe_emi_true'].values
    
    # Standardize
    print("Standardizing features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train scorecard
    print("Training scorecard...")
    scorecard = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    scorecard.fit(X_train_scaled, y_train_default)
    
    y_test_pred_proba = scorecard.predict_proba(X_test_scaled)[:, 1]
    test_auc = roc_auc_score(y_test_default, y_test_pred_proba)
    print(f"  Test AUC-ROC: {test_auc:.4f}")
    
    # Train capacity model
    print("Training capacity model...")
    capacity_model = Ridge(alpha=1.0, random_state=42)
    capacity_model.fit(X_train_scaled, y_train_emi)
    
    y_test_emi_pred = capacity_model.predict(X_test_scaled)
    y_test_emi_pred = np.minimum(y_test_emi_pred, 100000)  # Policy cap
    test_mae = mean_absolute_error(y_test_emi, y_test_emi_pred)
    print(f"  Test MAE: Rs {test_mae:,.0f}")
    
    # Save models
    print("Saving models...")
    models_dir = Path('ml/models')
    models_dir.mkdir(exist_ok=True)
    
    with open(models_dir / 'scorecard.pkl', 'wb') as f:
        pickle.dump(scorecard, f)
    with open(models_dir / 'capacity_model.pkl', 'wb') as f:
        pickle.dump(capacity_model, f)
    with open(models_dir / 'scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    with open(models_dir / 'feature_columns.pkl', 'wb') as f:
        pickle.dump(feature_cols, f)
    
    config = {
        'feature_count': len(feature_cols),
        'scorecard_auc': float(test_auc),
        'capacity_mae': float(test_mae),
    }
    with open(models_dir / 'config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ Training complete!")
    print(f"✓ Models saved to ml/models/")

if __name__ == '__main__':
    main()
```

Run it:
```bash
python ml/train_models.py
```

## Model Performance Expectations

Based on synthetic data generation:

| Metric | Typical Value |
|--------|---|
| Scorecard AUC-ROC | 0.75-0.85 |
| Scorecard Accuracy | 75-85% |
| Capacity MAE | Rs 2,000-5,000 |
| Confidence | 0.7-0.9 |

## Troubleshooting

### Model not improving
- Check data quality (missing values, outliers)
- Try different regularization (alpha, C parameter)
- Consider feature engineering

### Poor test performance
- Generator 1 and 2 may have different distributions
- Check for feature leakage
- Verify train/test split is by shop, not row

### Runtime memory issues
- Process one generator at a time
- Reduce batch size if batching
- Use sparse matrices for large feature sets

## Next: Deployment

Once models are trained and validated:

1. **Backend integration**: Load pickled models in API
2. **API endpoint**: Expose `/score` endpoint
3. **Frontend integration**: Call scoring API on application
4. **Monitoring**: Track model performance in production

See main README for API integration instructions.
