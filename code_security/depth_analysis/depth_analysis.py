import json
from collections import defaultdict


def analyze_depth_distribution(depths_file: str):
    """
    Analyze the depth distribution from saved file.
    
    Args:
        depths_file: Path to the saved depth analysis JSON
    """
    # Load depths
    with open(depths_file, 'r') as f:
        depth_data = json.load(f)
    
    print("=" * 80)
    print("CWE DEPTH DISTRIBUTION ANALYSIS")
    print("=" * 80)
    print(f"\nTotal CWEs: {len(depth_data)}\n")
    
    # Group by type
    type_depths = defaultdict(list)
    for cwe_id, info in depth_data.items():
        cwe_type = info['type']
        depth = info['depth']
        type_depths[cwe_type].append(depth)
    
    # Analyze each type
    type_order = [
        'pillar_weakness',
        'class_weakness',
        'base_weakness',
        'variant_weakness',
        'compound_weakness',
        'chain_weakness'
    ]
    
    for cwe_type in type_order:
        if cwe_type not in type_depths:
            continue
        
        depths = sorted(type_depths[cwe_type])
        n = len(depths)
        
        # Calculate statistics
        depth_min = min(depths)
        depth_max = max(depths)
        depth_mean = sum(depths) / n
        depth_median = depths[n // 2]
        
        # Count leaves (depth = 0)
        leaves = sum(1 for d in depths if d == 0)
        leaf_pct = (leaves / n) * 100
        
        print(f"{cwe_type.upper().replace('_', ' ')}")
        print(f"  Count:     {n}")
        print(f"  Min:       {depth_min}")
        print(f"  Max:       {depth_max}")
        print(f"  Mean:      {depth_mean:.2f}")
        print(f"  Median:    {depth_median}")
        print(f"  Leaves:    {leaves} ({leaf_pct:.1f}%)")
        
        # Show distribution
        print(f"  Distribution:")
        dist = defaultdict(int)
        for d in depths:
            dist[d] += 1
        
        for depth in sorted(dist.keys()):
            count = dist[depth]
            pct = (count / n) * 100
            bar = '█' * min(int(pct / 2), 40)
            print(f"    Depth {depth}: {count:4d} ({pct:5.1f}%) {bar}")
        
        print()

def main():
    """Main execution: calculate depths and analyze."""
    print("\nAnalyzing depth distribution...")
    analyze_depth_distribution(depths_file="code_security/depth_analysis/cwe_depths.json")


if __name__ == "__main__":
    # If you've already saved cwe_depths.json, just analyze it
    try:
        main()
    except FileNotFoundError:
        print("ERROR: cwe_depths.json not found!")
        print("\nTo generate it, uncomment the Step 1 section in main()")
        print("and make sure your paths are correct.")