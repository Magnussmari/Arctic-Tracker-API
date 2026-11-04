#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""
Export data for Figure 1 and Figure 2 into a single Excel file with multiple sheets
"""

import json
from pathlib import Path
import pandas as pd

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

def prepare_figure1_data(data):
    """Prepare all Figure 1 data"""

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

    # Sort by wild-origin count
    species_data.sort(key=lambda x: x['wild_origin_count'], reverse=True)
    top15 = species_data[:15]

    # Panel A: Top 15 Wild-Origin Species
    df_top15 = pd.DataFrame([
        {
            'Rank': i,
            'Common Name': sp['common_name'],
            'Scientific Name': sp['scientific_name'],
            'Wild-Origin Records': sp['wild_origin_count'],
            'Total Trade Records': sp['total_trade_records'],
            'IUCN Status': sp['iucn_status'],
            'CITES Appendix': sp['cites_appendix']
        }
        for i, sp in enumerate(top15, 1)
    ])

    # Panel B: Species Count by CITES Appendix
    appendix_counts = {}
    for sp in species_data:
        app = sp['cites_appendix']
        appendix_counts[app] = appendix_counts.get(app, 0) + 1

    df_appendix_count = pd.DataFrame([
        {'CITES Appendix': app, 'Species Count': appendix_counts[app]}
        for app in ['I', 'II', 'III', 'I/II'] if app in appendix_counts
    ])

    # Panel C: Trade Volume by CITES Appendix
    appendix_trade = {}
    for sp in species_data:
        app = sp['cites_appendix']
        appendix_trade[app] = appendix_trade.get(app, 0) + sp['total_trade_records']

    df_appendix_trade = pd.DataFrame([
        {'CITES Appendix': app, 'Total Trade Records': appendix_trade[app]}
        for app in ['I', 'II', 'III', 'I/II'] if app in appendix_trade
    ])

    return df_top15, df_appendix_count, df_appendix_trade

def prepare_figure2_data(data):
    """Prepare all Figure 2 data"""

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

    # Sort by total trade
    species_list.sort(key=lambda x: x['total_trade'], reverse=True)
    top10 = species_list[:10]

    # Panel A: Top 10 Most-Traded Species
    df_top10 = pd.DataFrame([
        {
            'Rank': i,
            'Common Name': sp['common_name'],
            'Scientific Name': sp['scientific_name'],
            'Total Trade Records': sp['total_trade'],
            'Wild-Origin Records': sp['wild_origin'],
            'IUCN Status': sp['iucn'],
            'CITES Appendix': sp['appendix']
        }
        for i, sp in enumerate(top10, 1)
    ])

    # Panel B: Trade by CITES Appendix
    appendix_trade = {}
    for sp in species_list:
        app = sp['appendix']
        appendix_trade[app] = appendix_trade.get(app, 0) + sp['total_trade']

    df_appendix_trade = pd.DataFrame([
        {'CITES Appendix': app, 'Total Trade Records': appendix_trade[app]}
        for app in ['I', 'II', 'III', 'I/II'] if app in appendix_trade
    ])

    # Panel C: Trade by Purpose Category
    purpose_trade = {}
    for sp in species_list:
        p = sp['purpose']
        p_name = PURPOSE_CODES.get(p, p)
        purpose_trade[p_name] = purpose_trade.get(p_name, 0) + sp['total_trade']

    df_purpose = pd.DataFrame([
        {'Trade Purpose': purpose, 'Total Trade Records': count}
        for purpose, count in sorted(purpose_trade.items(), key=lambda x: x[1], reverse=True)
    ])

    return df_top10, df_appendix_trade, df_purpose

def main():
    print("=" * 70)
    print("EXPORTING EXCEL FILE FOR FIGURES 1 & 2")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    data = load_data()

    # Prepare Figure 1 data
    print("Preparing Figure 1 data...")
    fig1_top15, fig1_appendix_count, fig1_appendix_trade = prepare_figure1_data(data)

    # Prepare Figure 2 data
    print("Preparing Figure 2 data...")
    fig2_top10, fig2_appendix_trade, fig2_purpose = prepare_figure2_data(data)

    # Create output directory
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)

    # Export to Excel with multiple sheets
    excel_file = output_dir / 'figures_data_for_publication.xlsx'
    print(f"\nWriting Excel file: {excel_file.name}")

    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Figure 1 sheets
        fig1_top15.to_excel(writer, sheet_name='Fig1_Top15_WildOrigin', index=False)
        fig1_appendix_count.to_excel(writer, sheet_name='Fig1_Species_by_Appendix', index=False)
        fig1_appendix_trade.to_excel(writer, sheet_name='Fig1_Trade_by_Appendix', index=False)

        # Figure 2 sheets
        fig2_top10.to_excel(writer, sheet_name='Fig2_Top10_TotalTrade', index=False)
        fig2_appendix_trade.to_excel(writer, sheet_name='Fig2_Trade_by_Appendix', index=False)
        fig2_purpose.to_excel(writer, sheet_name='Fig2_Trade_by_Purpose', index=False)

        # Add a summary sheet
        summary_data = {
            'Sheet Name': [
                'Fig1_Top15_WildOrigin',
                'Fig1_Species_by_Appendix',
                'Fig1_Trade_by_Appendix',
                'Fig2_Top10_TotalTrade',
                'Fig2_Trade_by_Appendix',
                'Fig2_Trade_by_Purpose'
            ],
            'Description': [
                'Figure 1, Panel A: Top 15 species by wild-origin trade',
                'Figure 1, Panel B: Species count by CITES Appendix',
                'Figure 1, Panel C: Trade volume by CITES Appendix',
                'Figure 2, Panel A: Top 10 species by total trade volume',
                'Figure 2, Panel B: Trade volume by CITES Appendix',
                'Figure 2, Panel C: Trade volume by purpose category'
            ],
            'Rows': [
                len(fig1_top15),
                len(fig1_appendix_count),
                len(fig1_appendix_trade),
                len(fig2_top10),
                len(fig2_appendix_trade),
                len(fig2_purpose)
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='README', index=False)

    print(f"✅ Excel file created successfully!")
    print(f"\nFile size: {excel_file.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 70)
    print("EXCEL FILE CONTENTS:")
    print("=" * 70)
    print("\nSheets included:")
    print("  1. README - Overview of all sheets")
    print("  2. Fig1_Top15_WildOrigin - Top 15 wild-origin species")
    print("  3. Fig1_Species_by_Appendix - Species distribution")
    print("  4. Fig1_Trade_by_Appendix - Trade volume distribution")
    print("  5. Fig2_Top10_TotalTrade - Top 10 most-traded species")
    print("  6. Fig2_Trade_by_Appendix - Trade by appendix")
    print("  7. Fig2_Trade_by_Purpose - Trade by purpose category")

    print("\n" + "=" * 70)
    print(f"✅ Ready to use.")
    print(f"\nLocation: {excel_file}")
    print("=" * 70)

if __name__ == '__main__':
    main()
