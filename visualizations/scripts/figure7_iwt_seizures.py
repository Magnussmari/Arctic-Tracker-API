#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""
Figure 7: Top Ten CITES-listed Arctic Species in IWT Seizures

Analysis of illegal wildlife trade (IWT) based on CITES database records
where source='I' (confiscated/seized items).

UPDATED LAYOUT:
- Siberian sturgeon separated into its own panel (skews data at 93.3%)
- Remaining 9 species shown without distortion
- Larger panels for better readability
- No main title (publication-ready)

Data Period: 1980-2023 (43 years)
Analysis Date: November 12, 2025


SUPERSEDED FOR THE MANUSCRIPT, 1 October 2026.
-----------------------------------------------
This script draws seizures from the CITES Trade Database where source='I', in
units of items seized. The manuscript's Figure 7 caption describes something
else: a count of seizure RECORDS from the Stringham et al. dataset, n = 225
across 26 species, with no unit of quantity because the source records none.
That figure is drawn by deposit/build_figure8_journal.py (renamed from
build_figure7_journal.py on 18 October 2026, when the manuscript's new Figure 5
moved this figure to 8). A later Figure 8 caption draft describes THIS view
(source code I, 595,487 units across 409 records for the sturgeon), so the two
artworks are both kept and the caption determines which one ships.

This file is kept because the CITES source='I' view is a real and separate
analysis, and deleting it would destroy the record of what the earlier figure
actually was. It must not be used to produce manuscript Figure 7.
"""

import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import Counter
from figure_output import save_figure

# IUCN Colors (standardized)
IUCN_COLORS = {
    'CR': '#D81E05',  # Critically Endangered - Red
    'EN': '#FC7F3F',  # Endangered - Orange
    'VU': '#F9E814',  # Vulnerable - Yellow
    'NT': '#CCE226',  # Near Threatened - Light Green
    'LC': '#60C659',  # Least Concern - Green
    'DD': '#D1D1C6',  # Data Deficient - Grey
}

# CITES Appendix Colors
CITES_COLORS = {
    'I': '#D81E05',   # Appendix I - Dark Red
    'II': '#FC7F3F',  # Appendix II - Orange
    'III': '#F9E814', # Appendix III - Yellow
}

# CITES Purpose code descriptions
PURPOSE_CODES = {
    'T': 'Commercial',
    'P': 'Personal',
    'H': 'Trophy',
    'S': 'Scientific',
    'E': 'Educational',
    'M': 'Medical',
    'N': 'Reintroduction',
    'B': 'Breeding',
    'Z': 'Zoo',
    'Q': 'Circus',
    'L': 'Law Enforcement',
    '': 'Unknown'
}

def load_iwt_data():
    """Load IWT seizure analysis data"""
    data_file = Path(__file__).parent.parent.parent / 'data/exports/iwt_seizures_analysis.json'

    if not data_file.exists():
        print(f"Error: Data file not found at {data_file}")
        print("Please run visualizations/data_processing/analyze_iwt_seizures_pg.py first to generate the data.")
        return None

    with open(data_file, 'r') as f:
        return json.load(f)

def create_figure():
    """Create IWT seizure visualization with Siberian sturgeon separated"""
    print("=" * 80)
    print("FIGURE 7: IWT SEIZURES - REDESIGNED LAYOUT")
    print("=" * 80)

    # Load data
    print("\n[1] Loading IWT seizure data...")
    data = load_iwt_data()

    if not data:
        return None

    all_species = data['top_10_species']
    print(f"✓ Loaded {len(all_species)} species records")

    # Separate Siberian sturgeon from others
    print("\n[2] Separating Siberian sturgeon from remaining species...")
    sturgeon = None
    other_species = []

    for s in all_species:
        if 'sturgeon' in s['common_name'].lower():
            sturgeon = s
        else:
            other_species.append(s)

    print(f"✓ Siberian sturgeon: {sturgeon['total_quantity']:,.0f} items ({sturgeon['seizure_count']} incidents)")
    print(f"✓ Other 9 species: {sum(s['total_quantity'] for s in other_species):,.0f} items")

    # Calculate totals for comparison
    sturgeon_total = sturgeon['total_quantity']
    others_total = sum(s['total_quantity'] for s in other_species)
    total_all = sturgeon_total + others_total

    # Prepare data for other 9 species
    print("\n[3] Preparing data for visualizations...")

    species_names = [s['common_name'] for s in other_species]
    species_quantities = [s['total_quantity'] for s in other_species]
    species_seizures = [s['seizure_count'] for s in other_species]
    species_colors = [IUCN_COLORS.get(s['iucn_status'], '#999') for s in other_species]

    # IUCN status aggregation (excluding sturgeon)
    iucn_totals = {}
    for s in other_species:
        status = s['iucn_status']
        iucn_totals[status] = iucn_totals.get(status, 0) + s['total_quantity']

    # CITES appendix aggregation (excluding sturgeon)
    cites_totals = {}
    for s in other_species:
        app = s['cites_appendix']
        cites_totals[app] = cites_totals.get(app, 0) + s['total_quantity']

    # Product aggregation (excluding sturgeon)
    product_counter = Counter()
    for s in other_species:
        for product, count in s['top_products'].items():
            product_counter[product] += count

    top_products = product_counter.most_common(10)
    product_labels = [p[0].title() for p in top_products]
    product_values = [p[1] for p in top_products]

    # Purpose aggregation (excluding sturgeon)
    purpose_counter = Counter()
    for s in other_species:
        for code, count in s['top_purposes'].items():
            purpose_counter[code] += count

    purpose_data = sorted(purpose_counter.items(), key=lambda x: x[1], reverse=True)
    purpose_labels = [PURPOSE_CODES.get(p[0], p[0]) for p in purpose_data]
    purpose_values = [p[1] for p in purpose_data]

    print("✓ Data prepared for all panels")

    # Create figure with larger panels
    print("\n[4] Creating visualization layout...")

    fig = make_subplots(
        rows=3, cols=2,
        row_heights=[0.30, 0.35, 0.35],
        column_widths=[0.5, 0.5],
        subplot_titles=(
            '<b>(a)</b> Siberian Sturgeon Dominance in IWT Seizures',
            '<b>(b)</b> Remaining 9 Species - Seizures by IUCN Status',
            '<b>(c)</b> Distribution by CITES Appendix (excl. sturgeon)',
            '<b>(d)</b> Product Types (excl. sturgeon)',
            '<b>(e)</b> Top 9 Species by Seizure Volume',
            '<b>(f)</b> Market Categories (excl. sturgeon)'
        ),
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "pie"}, {"type": "bar"}],
            [{"type": "bar", "colspan": 1}, {"type": "bar"}]
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.15
    )

    # Panel (a): Siberian Sturgeon vs Others - Comparison
    comparison_labels = ['Siberian sturgeon<br>(Critically Endangered)', 'All other 9 species<br>combined']
    comparison_values = [sturgeon_total, others_total]
    comparison_colors = [IUCN_COLORS['CR'], '#888888']
    # The two shares were hardcoded as 93.3% and 6.7% while the item and incident
    # counts beside them were computed live. Against the current corpus the true
    # split is 83.6/16.4, so the figure asserted a percentage its own bars
    # contradicted. Derived here so the three numbers in a label cannot disagree.
    iwt_total = sturgeon_total + others_total
    sturgeon_share = 100 * sturgeon_total / iwt_total if iwt_total else 0
    others_share = 100 - sturgeon_share
    other_incidents = sum(s["seizure_count"] for s in other_species)
    comparison_text = [
        f'{sturgeon_total:,.0f} items<br>{sturgeon_share:.1f}% of total<br>{sturgeon["seizure_count"]} incidents',
        f'{others_total:,.0f} items<br>{others_share:.1f}% of total<br>{other_incidents} incidents'
    ]

    fig.add_trace(
        go.Bar(
            x=comparison_labels,
            y=comparison_values,
            marker=dict(color=comparison_colors),
            text=comparison_text,
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Items Seized: %{y:,.0f}<extra></extra>',
            showlegend=False
        ),
        row=1, col=1
    )

    # Panel (b): IUCN Status (excluding sturgeon) - Horizontal Bar
    iucn_labels = list(iucn_totals.keys())
    iucn_values = list(iucn_totals.values())
    iucn_colors_list = [IUCN_COLORS.get(status, '#999') for status in iucn_labels]

    fig.add_trace(
        go.Bar(
            y=iucn_labels,
            x=iucn_values,
            orientation='h',
            marker=dict(color=iucn_colors_list),
            text=[f'{v:,.0f}' for v in iucn_values],
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Items Seized: %{x:,.0f}<extra></extra>',
            showlegend=False
        ),
        row=1, col=2
    )

    # Panel (c): CITES Appendix (excluding sturgeon) - Pie Chart
    cites_labels = [f"Appendix {k}" for k in cites_totals.keys()]
    cites_values = list(cites_totals.values())
    cites_colors_list = [CITES_COLORS.get(k, '#999') for k in cites_totals.keys()]

    fig.add_trace(
        go.Pie(
            labels=cites_labels,
            values=cites_values,
            marker=dict(colors=cites_colors_list),
            textposition='inside',
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Items: %{value:,.0f}<br>Percent: %{percent}<extra></extra>',
            showlegend=False
        ),
        row=2, col=1
    )

    # Panel (d): Product Types (excluding sturgeon)
    fig.add_trace(
        go.Bar(
            x=product_labels,
            y=product_values,
            marker=dict(color='#0288d1'),
            text=[f'{v}' for v in product_values],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Seizure records: %{y}<extra></extra>',
            showlegend=False
        ),
        row=2, col=2
    )

    # Panel (e): Top 9 Species (excluding sturgeon) - Bar Chart
    fig.add_trace(
        go.Bar(
            x=species_names,
            y=species_quantities,
            marker=dict(color=species_colors),
            text=[f'{v:,.0f}' for v in species_quantities],
            textposition='outside',
            name='Items Seized',
            hovertemplate='<b>%{x}</b><br>Items: %{y:,.0f}<extra></extra>',
            showlegend=False
        ),
        row=3, col=1
    )

    # Panel (f): Purpose Codes (excluding sturgeon)
    fig.add_trace(
        go.Bar(
            x=purpose_labels,
            y=purpose_values,
            marker=dict(color='#f57c00'),
            text=[f'{v}' for v in purpose_values],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Incidents: %{y}<extra></extra>',
            showlegend=False
        ),
        row=3, col=2
    )

    # Update layout with title annotation
    fig.update_layout(
        font=dict(family='Arial, sans-serif', size=12),
        showlegend=False,
        height=1400,
        width=1600,
        plot_bgcolor='white',
        paper_bgcolor='white',
        # b=120 clipped both footnotes: the five-line note sits at y=-0.07 and
        # the source line at y=-0.22, which is 255 px below the plot area.
        margin=dict(t=120, b=440, l=100, r=100)
    )

    # Add title annotation at top
    fig.add_annotation(
        text='<b>Arctic Species in Illegal Wildlife Trade Seizures</b><br>' +
             '<span style="font-size:13px">CITES confiscated/seized records • Data Period: 1980–2023 (43 years)</span>',
        xref='paper', yref='paper',
        x=0.5, y=1.02,
        xanchor='center', yanchor='bottom',
        showarrow=False,
        font=dict(size=16, family='Arial, sans-serif', color='#1a1a1a'),
        align='center'
    )

    # Update axes
    fig.update_xaxes(title_text='', row=1, col=1, showgrid=False, tickangle=-45)
    fig.update_yaxes(title_text='Items Seized', row=1, col=1, showgrid=True, gridcolor='#E5E5E5')

    fig.update_xaxes(title_text='Items Seized', row=1, col=2, showgrid=True, gridcolor='#E5E5E5')
    fig.update_yaxes(title_text='', row=1, col=2, showgrid=False)

    fig.update_xaxes(title_text='', row=2, col=2, tickangle=-45, showgrid=False)
    fig.update_yaxes(title_text='Seizure Records', row=2, col=2, showgrid=True, gridcolor='#E5E5E5')

    # Nine long species names at -45 degrees overprint each other: the render
    # of 2026-08 showed 'American River Otter' with its first word hidden
    # behind its neighbour. Upright labels at a smaller size fit.
    fig.update_xaxes(title_text='', row=3, col=1, tickangle=-90,
                     tickfont=dict(size=10), showgrid=False)
    fig.update_yaxes(title_text='Items Seized', row=3, col=1, showgrid=True, gridcolor='#E5E5E5')

    fig.update_xaxes(title_text='', row=3, col=2, tickangle=-45, showgrid=False)
    fig.update_yaxes(title_text='Incident Count', row=3, col=2, showgrid=True, gridcolor='#E5E5E5')

    # Add prominent note about data skew at the bottom
    fig.add_annotation(
        # Every number in this note was hardcoded and every one had gone stale:
        # 93.3% against a real 83.6%, 363,507 items against 594,431, 260
        # incidents against 392, and a "total dataset" of 389,783 items and 793
        # incidents that matched no quantity in the data at all.
        text=(f'<b>NOTE:</b> Siberian sturgeon (Acipenser baerii) seizures account for '
              f'{sturgeon_share:.1f}% of total IWT volume ({sturgeon_total:,.0f} items in '
              f'{sturgeon["seizure_count"]} incidents)<br>'
              'and have been separated into panel (a) to avoid distorting the scale of other species. '
              'Panels (b-f) show remaining 9 species<br>'
              'without sturgeon data. Despite Critically Endangered status, sturgeon is only listed '
              'under CITES Appendix II (controlled trade),<br>'
              'creating enforcement loopholes that facilitate massive illegal caviar trade. '
              f'Total dataset: {iwt_total:,.0f} units, '
              f'{sturgeon["seizure_count"] + other_incidents} incidents (1980-2023).<br>'
              # Stating a limitation is not the same as choosing a measure. The
              # CITES quantity field carries no common unit: for sturgeon these
              # totals are 312,267 g, 259,446 unitless counts, 17,906 kg, 3,322
              # specimens, 2,315 mg and 231 ml added together, so the 17.9 tonnes
              # contributes a smaller number than the 312 kg. Which measure the
              # paper should use is the authors' decision; leaving the share
              # unqualified while that is open is not.
              f'<b>Unit caveat:</b> quantities are the CITES quantity field summed '
              f'across mixed units (kg, g, ml, specimens and unitless counts), so a '
              f'share of "volume" is not a share of one physical quantity. Incident '
              f'counts are dimensionless and comparable.'),
        xref='paper', yref='paper',
        x=0.5, y=-0.155,   # clear of the upright species labels in panel (e)
        xanchor='center', yanchor='top',
        showarrow=False,
        font=dict(size=11, family='Arial, sans-serif', color='#333'),
        bgcolor='rgba(255,250,205,0.9)',
        bordercolor='#d32f2f',
        borderwidth=2,
        borderpad=12,
        align='left'
    )

    # Add data quality note
    fig.add_annotation(
        text='<b>Data Source:</b> CITES Trade Database (source=\'I\' confiscated/seized) • <b>IUCN Status:</b> Latest assessments • <b>CITES Appendix:</b> Current listings',
        xref='paper', yref='paper',
        x=0.5, y=-0.30,   # below the note box, which ends around -0.26
        xanchor='center', yanchor='top',
        showarrow=False,
        font=dict(size=10, family='Arial, sans-serif', color='#666'),
        align='center'
    )

    print("✓ Figure created successfully")

    return fig

def main():
    """Generate and save Figure 7"""
    fig = create_figure()

    if fig is None:
        print("\n❌ Failed to create figure")
        return

    # Save to HTML
    output_dir = Path(__file__).parent.parent / 'production'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'figure7_iwt_seizures.html'

    print(f"\n[5] Saving figure to: {output_file}")
    save_figure(fig, 'figure7_iwt_seizures', width=1600, height=1400)

    print("\n" + "=" * 80)
    print("FIGURE 7 GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nView figure at: {output_file}")
    print(f"Open in browser: file://{output_file.absolute()}")

if __name__ == '__main__':
    main()
