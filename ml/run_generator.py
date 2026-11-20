"""
Entry point to generate all synthetic data and build features.

Usage:
    python ml/run_generator.py [--gen 1|2|all] [--with-features]
"""

import argparse
import logging
from pathlib import Path

from generator import generate_and_save, SyntheticDataGenerator
from generator_config import get_config
from feature_builder import build_feature_matrix


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic UdyamCred datasets'
    )
    parser.add_argument(
        '--gen',
        type=str,
        default='all',
        choices=['1', '2', 'all'],
        help='Which generator to run (default: all)'
    )
    parser.add_argument(
        '--with-features',
        action='store_true',
        help='Also build feature matrices after generation'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='ml/data',
        help='Output directory for data (default: ml/data)'
    )
    
    args = parser.parse_args()
    setup_logging()
    
    # Create output directory
    Path(args.data_dir).mkdir(parents=True, exist_ok=True)
    
    # Determine which generators to run
    generators = []
    if args.gen == 'all':
        generators = [1, 2]
    else:
        generators = [int(args.gen)]
    
    # Generate datasets
    for gen_id in generators:
        print(f"\n{'='*60}")
        print(f"GENERATING DATASET: Generator {gen_id}")
        print(f"{'='*60}\n")
        
        try:
            generate_and_save(gen_id, output_dir=args.data_dir)
        except Exception as e:
            logging.error(f"Failed to generate dataset for generator {gen_id}: {e}")
            raise
    
    # Build feature matrices if requested
    if args.with_features:
        print(f"\n{'='*60}")
        print("BUILDING FEATURE MATRICES")
        print(f"{'='*60}\n")
        
        for gen_id in generators:
            try:
                print(f"\nBuilding features for Generator {gen_id}...")
                features = build_feature_matrix(gen_id, lookback_months=12, data_dir=args.data_dir)
                features_path = Path(args.data_dir) / f'features_gen{gen_id}.csv'
                features.to_csv(features_path, index=False)
                print(f"✓ Saved {features_path}")
                print(f"  Shape: {features.shape}")
                print(f"  Memory: {features.memory_usage(deep=True).sum() / 1e6:.1f} MB")
            except Exception as e:
                logging.error(f"Failed to build features for generator {gen_id}: {e}")
                raise
    
    print(f"\n{'='*60}")
    print("GENERATION COMPLETE")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
