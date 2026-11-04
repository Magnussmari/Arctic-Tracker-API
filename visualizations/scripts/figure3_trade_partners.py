#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""
Figure 3: Arctic Species Trade Networks
Top 10 non-Arctic states trading in Arctic species and their top 5 Arctic trade partners

Data Period: 1975-2024 (50 years)
"""

import sys
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import defaultdict

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'data_processing'))

from pg_common import query  # psycopg2 vs sovereign arctic DB (retargeted 2026-07-22)
from figure_output import save_figure
import os as _os
SCHEMA = _os.environ.get("ARCTIC_SCHEMA", "arctic_v2")

# Arctic states (ISO 2-letter codes)
ARCTIC_STATES = {
    'CA',  # Canada
    'US',  # United States
    'RU',  # Russia
    'NO',  # Norway
    'IS',  # Iceland
    'DK',  # Denmark (includes Greenland in trade records)
    'SE',  # Sweden
    'FI',  # Finland
    'GL',  # Greenland (sometimes separate)
}

# Country code to name mapping (common ones)
COUNTRY_NAMES = {
    'US': 'United States',
    'DE': 'Germany',
    'CN': 'China',
    'JP': 'Japan',
    'GB': 'United Kingdom',
    'FR': 'France',
    'IT': 'Italy',
    'ES': 'Spain',
    'NL': 'Netherlands',
    'BE': 'Belgium',
    'CH': 'Switzerland',
    'AT': 'Austria',
    'KR': 'South Korea',
    'HK': 'Hong Kong',
    'SG': 'Singapore',
    'CA': 'Canada',
    'RU': 'Russia',
    'NO': 'Norway',
    'IS': 'Iceland',
    'DK': 'Denmark',
    'SE': 'Sweden',
    'FI': 'Finland',
    'GL': 'Greenland',
    'AE': 'United Arab Emirates',
    'QA': 'Qatar',
    'AU': 'Australia',
}

def get_country_name(code):
    """Get country name from code"""
    return COUNTRY_NAMES.get(code, code)

def analyze_trade_partners():
    """Query database and analyze trade partnerships"""
    print("=" * 70)
    print("ANALYZING TRADE PARTNERSHIPS")
    print("=" * 70)

    print("\nQuerying trade records (importer/exporter pairs, one aggregate query)...")

    # Same semantics as the legacy supabase pagination: count RECORDS (not
    # quantity), only rows with both importer and exporter present, year<=2024.
    pair_counts = query(f"""
        SELECT importer, exporter, count(*) AS n
        FROM {SCHEMA}.cites_trade_records
        WHERE year <= 2024
          AND importer IS NOT NULL AND importer <> ''
          AND exporter IS NOT NULL AND exporter <> ''
        GROUP BY importer, exporter
    """)

    # Analyze import patterns
    print("\nAnalyzing import patterns...")

    importer_totals = defaultdict(int)  # Total imports by country
    importer_arctic_partners = defaultdict(lambda: defaultdict(int))  # Imports from Arctic states

    for row in pair_counts:
        importer, exporter, n = row['importer'], row['exporter'], row['n']
        importer_totals[importer] += n
        if exporter in ARCTIC_STATES:
            importer_arctic_partners[importer][exporter] += n

    print(f"Retrieved {sum(importer_totals.values()):,} trade records")
    print(f"Found {len(importer_totals)} unique importing countries")

    # Filter to non-Arctic importers only
    non_arctic_importers = {
        country: count for country, count in importer_totals.items()
        if country not in ARCTIC_STATES and count > 0
    }

    print(f"Non-Arctic importers: {len(non_arctic_importers)}")

    # Get top 10 non-Arctic importers
    top10_importers = sorted(
        non_arctic_importers.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    print("\nTop 10 non-Arctic importers:")
    for i, (country, count) in enumerate(top10_importers, 1):
        print(f"  {i}. {get_country_name(country)} ({country}): {count:,} records")

    # For each top importer, get their top 5 Arctic partners
    trade_network = {}
    for country_code, total_imports in top10_importers:
        arctic_partners = importer_arctic_partners[country_code]

        # Get top 5 Arctic partners
        top5_partners = sorted(
            arctic_partners.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        trade_network[country_code] = {
            'name': get_country_name(country_code),
            'total_imports': total_imports,
            'arctic_partners': [
                {
                    'code': partner_code,
                    'name': get_country_name(partner_code),
                    'records': records
                }
                for partner_code, records in top5_partners
            ]
        }

    return trade_network

def create_figure(trade_network):
    """Create visualization of trade networks"""
    print("\nCreating visualization...")

    # Prepare data for visualization
    countries = []
    total_imports = []
    partner_info = []

    for country_code, data in trade_network.items():
        countries.append(data['name'])
        total_imports.append(data['total_imports'])

        # Create partner text
        partners_text = '<br>'.join([
            f"  {i}. {p['name']}: {p['records']:,} records"
            for i, p in enumerate(data['arctic_partners'], 1)
        ])
        partner_info.append(partners_text)

    # Create figure with 2 panels
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{'type': 'bar'}, {'type': 'table'}]],
        subplot_titles=(
            '<b>(a)</b> Top 10 Non-Arctic States Importing Arctic Species',
            '<b>(b)</b> Top 5 Arctic Trade Partners per Importer'
        ),
        horizontal_spacing=0.15,
        column_widths=[0.45, 0.55]
    )

    # Panel A: Bar chart of top 10 importers
    fig.add_trace(
        go.Bar(
            y=countries[::-1],
            x=total_imports[::-1],
            orientation='h',
            marker=dict(color='#2E5266'),
            text=[f"{v:,}" for v in total_imports[::-1]],
            textposition='auto',
            hovertemplate='%{y}<br>Total imports: %{x:,} records<extra></extra>'
        ),
        row=1, col=1
    )

    # Panel B: Table showing trade partnerships
    table_data = []
    for country_code, data in trade_network.items():
        for i, partner in enumerate(data['arctic_partners']):
            table_data.append({
                'Importer': data['name'],
                'Rank': i + 1,
                'Arctic Partner': partner['name'],
                'Trade Records': partner['records']
            })

    # Create table
    fig.add_trace(
        go.Table(
            header=dict(
                values=['<b>Importer</b>', '<b>Rank</b>', '<b>Arctic Partner</b>', '<b>Trade Records</b>'],
                fill_color='#2E5266',
                font=dict(color='white', size=12),
                align='left'
            ),
            cells=dict(
                values=[
                    [row['Importer'] for row in table_data],
                    [row['Rank'] for row in table_data],
                    [row['Arctic Partner'] for row in table_data],
                    [f"{row['Trade Records']:,}" for row in table_data]
                ],
                fill_color=[['white', '#F0F0F0'] * (len(table_data) // 2 + 1)],
                align='left',
                font=dict(size=11)
            )
        ),
        row=1, col=2
    )

    # Update layout
    fig.update_layout(
        title={
            # NO FIGURE NUMBER IN THE ARTWORK. This read "Figure 3", which is
            # the pipeline id; the manuscript prints this as Figure 8, and the
            # binding between the two lives in
            # visualizations/provenance/figure_provenance.json. A number drawn
            # into the image is a number that cannot be renumbered with the
            # paper, and this one was already wrong by five.
            'text': "<b>Global Trade Networks for Arctic Species (1975-2024)</b><br>" +
                    "<span style='font-size:11pt; color:#555;'>Trade flows between non-Arctic importers and Arctic source states</span>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'family': 'Arial, sans-serif'}
        },
        showlegend=False,
        height=900,
        width=1400,
        font=dict(family='Arial, sans-serif', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=150, b=80, l=80, r=80)
    )

    # Update axes
    fig.update_xaxes(
        title_text="Total Trade Records",
        title_font=dict(size=14),
        row=1, col=1,
        showgrid=True,
        gridcolor='#E5E5E5'
    )

    fig.update_yaxes(
        title_text="",
        row=1, col=1,
        showgrid=False
    )

    # Add note about Arctic states
    fig.add_annotation(
        text=('<b>Arctic States:</b> Canada, United States, Russia, Norway, '
              'Iceland, Denmark, Greenland, Sweden, Finland.<br>'
              'Denmark and Greenland are separate reporters in the Trade '
              'Database and are counted separately here.'),
        xref='paper', yref='paper',
        x=0.5, y=-0.05,
        xanchor='center',
        showarrow=False,
        font=dict(size=11, family='Arial', color='#555')
    )

    return fig

def main():
    print("=" * 70)
    print("FIGURE 3: TRADE PARTNERSHIPS")
    print("=" * 70)

    # Analyze trade partnerships
    trade_network = analyze_trade_partners()

    # Create figure
    fig = create_figure(trade_network)

    # Create output directory
    output_dir = Path(__file__).parent.parent / 'production'
    output_dir.mkdir(exist_ok=True)

    # Save HTML
    output_file = output_dir / 'figure3_trade_partners.html'
    print(f"\nSaving to: {output_file}")

    # 50 body rows (10 importers x 5 partners) plus the header have to fit, or
    # panel (b) silently drops its tail -- the 2026-08 render showed Singapore
    # with two partners and the caption promising five.
    rows = sum(len(d['arctic_partners']) for d in trade_network.values())
    if rows != 50:
        raise SystemExit(f"panel (b) would draw {rows} partner rows, not 50; "
                         f"the caption says five per importer")
    save_figure(fig, 'figure3_trade_partners', width=1600, height=1500)

    print(f"✅ Saved successfully!")
    print(f"\nFile size: {output_file.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 70)
    print("FIGURE 3 COMPLETE")
    print("=" * 70)
    print(f"\nOpen with:")
    print(f"  open {output_file}")
    print("=" * 70)

if __name__ == '__main__':
    main()
