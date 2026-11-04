#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""
Export CSV data files for Figure 1 and Figure 2
"""

import json
import csv
from pathlib import Path

# Purpose codes
PURPOSE_CODES = {
    'T': 'Commercial',
    'P': 'Personal',
    'S': 'Scientific',
    'H': 'Hunting Trophy',
    'E': 'Educational',
    'B': 'Breeding',
    'L': 'Law Enforcement',
    'M': 'Medical',
    'Q': 'Circus/Exhibition',
    'Z': 'Zoo'
}

def load_data():
    """Load CITES effectiveness data"""
    # The effectiveness JSON is a legacy input that is not part of the public
    # release. ARCTIC_EFFECTIVENESS_JSON overrides the repository location.
    import os
    data_file = Path(os.environ.get('ARCTIC_EFFECTIVENESS_JSON') or
                     Path(__file__).parent.parent.parent / 'data/raw/1_DATA_cites_effectiveness.json')
    if not data_file.is_file():
        raise SystemExit("skipped: the CITES effectiveness JSON is not part of the "
                         "public release (set ARCTIC_EFFECTIVENESS_JSON to run this export).")
    with open(data_file, 'r') as f:
        return json.load(f)

def normalize_iucn(iucn_raw):
    """Normalize IUCN status to abbreviations"""
    iucn_str = str(iucn_raw)
    if 'Least Concern' in iucn_str:
        return 'LC'
    elif 'Near Threatened' in iucn_str:
        return 'NT'
    elif 'Vulnerable' in iucn_str:
        return 'VU'
    elif 'Endangered' in iucn_str and 'Critically' not in iucn_str:
        return 'EN'
    elif 'Critically Endangered' in iucn_str:
        return 'CR'
    elif 'Data Deficient' in iucn_str:
        return 'DD'
    return iucn_raw

def export_figure1_csvs(data, output_dir):
    """Export CSV files for Figure 1"""

    # Prepare species data
    species_data = []
    for sp in data['species_analyses']:
        iucn_normalized = normalize_iucn(sp.get('iucn_status', 'LC'))

        species_data.append({
            'common_name': sp.get('common_name', 'Unknown'),
            'scientific_name': sp.get('scientific_name', ''),
            'wild_origin_count': sp.get('wild_origin_count', 0),
            'total_trade_records': sp.get('trade_records_count', 0),
            'iucn_status': iucn_normalized,
            'cites_appendix': sp.get('cites_appendix', 'Unknown'),
        })

    # Sort by wild-origin count and get top 15
    species_data.sort(key=lambda x: x['wild_origin_count'], reverse=True)
    top15 = species_data[:15]

    # 1. Export Top 15 Wild-Origin Species
    csv_file = output_dir / 'figure1_panel_a_top15_species.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'rank', 'common_name', 'scientific_name', 'wild_origin_records',
            'total_trade_records', 'iucn_status', 'cites_appendix'
        ])
        writer.writeheader()
        for i, sp in enumerate(top15, 1):
            writer.writerow({
                'rank': i,
                'common_name': sp['common_name'],
                'scientific_name': sp['scientific_name'],
                'wild_origin_records': sp['wild_origin_count'],
                'total_trade_records': sp['total_trade_records'],
                'iucn_status': sp['iucn_status'],
                'cites_appendix': sp['cites_appendix']
            })
    print(f"✅ Exported: {csv_file.name}")

    # 2. Export Species Count by CITES Appendix
    appendix_counts = {}
    for sp in species_data:
        app = sp['cites_appendix']
        appendix_counts[app] = appendix_counts.get(app, 0) + 1

    csv_file = output_dir / 'figure1_panel_b_species_by_appendix.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['cites_appendix', 'species_count'])
        writer.writeheader()
        for app in ['I', 'II', 'III', 'I/II']:
            if app in appendix_counts:
                writer.writerow({
                    'cites_appendix': app,
                    'species_count': appendix_counts[app]
                })
    print(f"✅ Exported: {csv_file.name}")

    # 3. Export Trade Volume by CITES Appendix
    appendix_trade = {}
    for sp in species_data:
        app = sp['cites_appendix']
        appendix_trade[app] = appendix_trade.get(app, 0) + sp['total_trade_records']

    csv_file = output_dir / 'figure1_panel_c_trade_by_appendix.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['cites_appendix', 'total_trade_records'])
        writer.writeheader()
        for app in ['I', 'II', 'III', 'I/II']:
            if app in appendix_trade:
                writer.writerow({
                    'cites_appendix': app,
                    'total_trade_records': appendix_trade[app]
                })
    print(f"✅ Exported: {csv_file.name}")

def export_figure2_csvs(data, output_dir):
    """Export CSV files for Figure 2"""

    # Prepare species data
    species_list = []
    for sp in data['species_analyses']:
        species_list.append({
            'common_name': sp.get('common_name', 'Unknown'),
            'scientific_name': sp.get('scientific_name', ''),
            'total_trade': sp.get('trade_records_count', 0),
            'wild_origin': sp.get('wild_origin_count', 0),
            'iucn': normalize_iucn(sp.get('iucn_status', 'LC')),
            'appendix': sp.get('cites_appendix', 'Unknown'),
            'purpose': sp.get('most_recorded_trade_use', 'Unknown'),
        })

    # Sort by total trade and get top 10
    species_list.sort(key=lambda x: x['total_trade'], reverse=True)
    top10 = species_list[:10]

    # 1. Export Top 10 Most-Traded Species
    csv_file = output_dir / 'figure2_panel_a_top10_traded_species.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'rank', 'common_name', 'scientific_name', 'total_trade_records',
            'wild_origin_records', 'iucn_status', 'cites_appendix'
        ])
        writer.writeheader()
        for i, sp in enumerate(top10, 1):
            writer.writerow({
                'rank': i,
                'common_name': sp['common_name'],
                'scientific_name': sp['scientific_name'],
                'total_trade_records': sp['total_trade'],
                'wild_origin_records': sp['wild_origin'],
                'iucn_status': sp['iucn'],
                'cites_appendix': sp['appendix']
            })
    print(f"✅ Exported: {csv_file.name}")

    # 2. Export Trade by CITES Appendix
    appendix_trade = {}
    for sp in species_list:
        app = sp['appendix']
        appendix_trade[app] = appendix_trade.get(app, 0) + sp['total_trade']

    csv_file = output_dir / 'figure2_panel_b_trade_by_appendix.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['cites_appendix', 'total_trade_records'])
        writer.writeheader()
        for app in ['I', 'II', 'III', 'I/II']:
            if app in appendix_trade:
                writer.writerow({
                    'cites_appendix': app,
                    'total_trade_records': appendix_trade[app]
                })
    print(f"✅ Exported: {csv_file.name}")

    # 3. Export Trade by Purpose Category
    purpose_trade = {}
    for sp in species_list:
        p = sp['purpose']
        p_name = PURPOSE_CODES.get(p, p)
        purpose_trade[p_name] = purpose_trade.get(p_name, 0) + sp['total_trade']

    csv_file = output_dir / 'figure2_panel_c_trade_by_purpose.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['trade_purpose', 'total_trade_records'])
        writer.writeheader()
        # Sort by trade volume
        for purpose, count in sorted(purpose_trade.items(), key=lambda x: x[1], reverse=True):
            writer.writerow({
                'trade_purpose': purpose,
                'total_trade_records': count
            })
    print(f"✅ Exported: {csv_file.name}")

def main():
    print("=" * 70)
    print("EXPORTING CSV DATA FOR FIGURES 1 & 2")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    data = load_data()

    # Create output directory
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)

    # Export Figure 1 CSVs
    print("\n--- FIGURE 1 EXPORTS ---")
    export_figure1_csvs(data, output_dir)

    # Export Figure 2 CSVs
    print("\n--- FIGURE 2 EXPORTS ---")
    export_figure2_csvs(data, output_dir)

    print("\n" + "=" * 70)
    print("✅ ALL CSV FILES EXPORTED SUCCESSFULLY")
    print("=" * 70)
    print(f"\nLocation: {output_dir}")
    print("\nFigure 1 files:")
    print("  - figure1_panel_a_top15_species.csv")
    print("  - figure1_panel_b_species_by_appendix.csv")
    print("  - figure1_panel_c_trade_by_appendix.csv")
    print("\nFigure 2 files:")
    print("  - figure2_panel_a_top10_traded_species.csv")
    print("  - figure2_panel_b_trade_by_appendix.csv")
    print("  - figure2_panel_c_trade_by_purpose.csv")
    print("=" * 70)

if __name__ == '__main__':
    main()
