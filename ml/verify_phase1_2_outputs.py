#!/usr/bin/env python
"""Verify Phase 1-2 data generation outputs."""

import pandas as pd

print('=== TIER_ASSIGNMENTS_GEN1.CSV ===')
df = pd.read_csv('ml/data/tier_assignments_gen1.csv')
print(df.head(10))
print(f'\nShape: {df.shape}')
print(f'\nTier distribution:')
print(df['tier'].value_counts().sort_index())

print('\n\n=== SOURCE_DATA_GEN1.CSV (first shop) ===')
df = pd.read_csv('ml/data/source_data_gen1.csv')
shop_id = df['shop_id'].iloc[0]
print(df[df['shop_id'] == shop_id].head(10))
print(f'\nShape: {df.shape}')
print(f'Non-null counts:')
print(f'  AA flows: {df["aa_flow"].notna().sum()}')
print(f'  GST flows: {df["gst_flow"].notna().sum()}')
print(f'  UPI flows: {df["upi_flow"].notna().sum()}')

print('\n\n=== VERIFIED_WINDOWS_GEN1.CSV ===')
df = pd.read_csv('ml/data/verified_windows_gen1.csv')
print(df.head(10))
print(f'\nShape: {df.shape}')
print(f'\nAgreement score stats:')
print(f'  Mean: {df["agreement_score"].mean():.3f}')
print(f'  Std: {df["agreement_score"].std():.3f}')
print(f'  Min: {df["agreement_score"].min():.3f}')
print(f'  Max: {df["agreement_score"].max():.3f}')
print(f'\nVerified months stats:')
print(f'  Mean: {df["months_verified"].mean():.1f}')
print(f'  Median: {df["months_verified"].median():.1f}')

print('\n\n=== PHOTOS_GEN1.CSV ===')
df = pd.read_csv('ml/data/photos_gen1.csv')
print(df.head(10))
print(f'\nShape: {df.shape}')
print(f'Verified: {df["verified"].sum()} / {len(df)} ({(df["verified"].mean()*100):.1f}%)')
print(f'\nPhoto types:')
print(df['photo_type'].value_counts())
