# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
# SCALE-EXEMPT: the dict the detector finds is a bar SORT ORDER for panel (b)
# (CR first, DD last) and nothing is ranked or compared with it. No
# trajectory, transition or reported number is computed from it.
"""
Colour note (2026-08-13). Green-and-red colouring in heatmaps, graphs and
schematics is replaced wherever the colours are chosen arbitrarily.

The two panels here were green and red-orange, and the colours meant nothing:
they distinguished one panel from another and carried no variable. That is
precisely the arbitrary case. They are now blue and
orange, which under deuteranopia separate by a CIE76 delta-E of 133 rather than
63, and under protanopia by 135 rather than 37.

The IUCN category palette elsewhere in this repository is a different matter and
is deliberately kept: it is the discipline's own scale and its colours are not
arbitrary. That figure carries the category as text instead, so hue is not the
only channel.
"""
#!/usr/bin/env python3
"""
Figure 8: Wild-Origin Trade Analysis for Arctic Species

Comprehensive analysis of legal wild-origin trade based on CITES database records
where source='W' (specimens taken from the wild).

Scope: 15 wild-origin species, 1985-2024. The totals are NOT restated here.
They are read from data/exports/wild_origin_trade_analysis.json at draw time and
written into the figure's summary box by the code below, because the numbers that
used to stand in this docstring and in that box were the ones from the 2025-11-12
run that the data file itself records as truncated at 51,000 rows.
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

def load_wild_trade_data():
    """Load wild-origin trade analysis data"""
    data_file = Path(__file__).parent.parent.parent / 'data/exports/wild_origin_trade_analysis.json'

    if not data_file.exists():
        print(f"Error: Data file not found at {data_file}")
        print("Please run visualizations/data_processing/analyze_wild_origin_trade_pg.py first to generate the data.")
        return None

    with open(data_file, 'r') as f:
        return json.load(f)

def create_figure():
    """Create comprehensive wild-origin trade visualization"""
    print("=" * 80)
    print("FIGURE 8: WILD-ORIGIN TRADE ANALYSIS - COMPREHENSIVE")
    print("=" * 80)

    # Load data
    print("\n[1] Loading wild-origin trade data...")
    data = load_wild_trade_data()

    if not data:
        return None

    all_species = data['top_15_species']
    print(f"✓ Loaded {len(all_species)} species records")
    print(f"✓ Total trade volume: {data['total_quantity']:,.0f} items")
    print(f"✓ Total records: {data['total_records']:,}")

    # Prepare data for visualizations
    print("\n[2] Preparing data for visualizations...")

    # Species data
    # The curated name table and the paper both say Roseroot; the export
    # still carries the old display name for Rhodiola rosea.
    LABEL = {'Arctic Rose': 'Roseroot'}
    species_names = [LABEL.get(s['common_name'], s['common_name'])
                     for s in all_species]
    species_quantities = [s['total_quantity'] for s in all_species]
    species_records = [s['record_count'] for s in all_species]
    species_colors = [IUCN_COLORS.get(s['iucn_status'], '#999') for s in all_species]
    species_statuses = [s['iucn_status'] for s in all_species]

    # IUCN status aggregation
    iucn_totals = {}
    for s in all_species:
        status = s['iucn_status']
        iucn_totals[status] = iucn_totals.get(status, 0) + s['total_quantity']

    # CITES appendix aggregation
    cites_totals = {}
    for s in all_species:
        app = s['cites_appendix']
        cites_totals[app] = cites_totals.get(app, 0) + s['total_quantity']

    # Product aggregation
    product_counter = Counter()
    for s in all_species:
        for product, count in s['top_products'].items():
            product_counter[product] += count

    top_products = product_counter.most_common(12)
    product_labels = [p[0].title() for p in top_products]
    product_values = [p[1] for p in top_products]

    # Purpose aggregation
    purpose_counter = Counter()
    for s in all_species:
        for code, count in s['top_purposes'].items():
            purpose_counter[code] += count

    purpose_data = sorted(purpose_counter.items(), key=lambda x: x[1], reverse=True)[:8]
    purpose_labels = [PURPOSE_CODES.get(p[0], p[0]) for p in purpose_data]
    purpose_values = [p[1] for p in purpose_data]

    # Exporter aggregation
    exporter_counter = Counter()
    for s in all_species:
        for country, count in s['top_exporters'].items():
            exporter_counter[country] += count

    top_exporters = exporter_counter.most_common(10)
    exporter_labels = [e[0] for e in top_exporters]
    exporter_values = [e[1] for e in top_exporters]

    # Importer aggregation
    importer_counter = Counter()
    for s in all_species:
        for country, count in s['top_importers'].items():
            importer_counter[country] += count

    top_importers = importer_counter.most_common(10)
    importer_labels = [i[0] for i in top_importers]
    importer_values = [i[1] for i in top_importers]

    print("✓ Data prepared for all panels")

    # Create figure with 6 panels
    print("\n[3] Creating visualization layout...")

    fig = make_subplots(
        rows=3, cols=2,
        row_heights=[0.35, 0.32, 0.33],
        column_widths=[0.5, 0.5],
        subplot_titles=(
            '<b>(a)</b> Top 15 Species by Wild-Origin Trade Volume',
            '<b>(b)</b> Trade Volume by IUCN Red List Status',
            '<b>(c)</b> Trade Volume by CITES Appendix',
            '<b>(d)</b> Product Types (Top 12 Categories)',
            '<b>(e)</b> Trade Purposes',
            '<b>(f)</b> Top Exporting Countries'
        ),
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "pie"}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "bar"}]
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.15
    )

    # Panel (a): Top 15 Species by Volume
    fig.add_trace(
        go.Bar(
            x=species_names,
            y=species_quantities,
            marker=dict(color=species_colors),
            text=[f'{v:,.0f}' for v in species_quantities],
            textposition='outside',
            customdata=list(zip(species_statuses, species_records)),
            hovertemplate='<b>%{x}</b><br>Items: %{y:,.0f}<br>IUCN: %{customdata[0]}<br>Records: %{customdata[1]:,}<extra></extra>',
            showlegend=False
        ),
        row=1, col=1
    )

    # Panel (b): IUCN Status - Horizontal Bar
    iucn_labels = list(iucn_totals.keys())
    iucn_values = list(iucn_totals.values())
    iucn_colors_list = [IUCN_COLORS.get(status, '#999') for status in iucn_labels]

    # Sort by conservation status severity (CR -> EN -> VU -> NT -> LC -> DD)
    status_order = {'CR': 0, 'EN': 1, 'VU': 2, 'NT': 3, 'LC': 4, 'DD': 5}
    sorted_iucn = sorted(zip(iucn_labels, iucn_values, iucn_colors_list),
                         key=lambda x: status_order.get(x[0], 99))
    iucn_labels_sorted, iucn_values_sorted, iucn_colors_sorted = zip(*sorted_iucn)

    fig.add_trace(
        go.Bar(
            y=list(iucn_labels_sorted),
            x=list(iucn_values_sorted),
            orientation='h',
            marker=dict(color=list(iucn_colors_sorted)),
            text=[f'{v:,.0f}' for v in iucn_values_sorted],
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Items: %{x:,.0f}<extra></extra>',
            showlegend=False
        ),
        row=1, col=2
    )

    # Panel (c): CITES Appendix - Pie Chart
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

    # Panel (d): Product Types
    fig.add_trace(
        go.Bar(
            x=product_labels,
            y=product_values,
            marker=dict(color='#1F6FB2'),  # Blue. See the note on arbitrary red-green below.
            text=[f'{v}' for v in product_values],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Records: %{y:,}<extra></extra>',
            showlegend=False
        ),
        row=2, col=2
    )

    # Panel (e): Trade Purposes
    fig.add_trace(
        go.Bar(
            x=purpose_labels,
            y=purpose_values,
            marker=dict(color='#1565C0'),  # Blue
            text=[f'{v:,}' for v in purpose_values],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Records: %{y:,}<extra></extra>',
            showlegend=False
        ),
        row=3, col=1
    )

    # Panel (f): Top Exporters
    fig.add_trace(
        go.Bar(
            x=exporter_labels,
            y=exporter_values,
            marker=dict(color='#E08214'),  # Orange, paired with the blue above
            text=[f'{v:,}' for v in exporter_values],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Records: %{y:,}<extra></extra>',
            showlegend=False
        ),
        row=3, col=2
    )

    # Update layout with title annotation
    fig.update_layout(
        font=dict(family='Arial, sans-serif', size=12),
        showlegend=False,
        height=1700,
        width=1800,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=120, b=280, l=100, r=100)
    )

    # Add title annotation at top
    fig.add_annotation(
        text='<b>Legal Wild-Origin Trade in Arctic Species</b><br>' +
             '<span style="font-size:13px">CITES wild-source records • Data Period: 1985–2024 (39 years)</span>',
        xref='paper', yref='paper',
        x=0.5, y=1.015,
        xanchor='center', yanchor='bottom',
        showarrow=False,
        font=dict(size=16, family='Arial, sans-serif', color='#1a1a1a'),
        align='center'
    )

    # Update axes
    fig.update_xaxes(title_text='', row=1, col=1, tickangle=-45, showgrid=False)
    fig.update_yaxes(title_text='Items Traded', row=1, col=1, showgrid=True, gridcolor='#E5E5E5')

    fig.update_xaxes(title_text='Items Traded', row=1, col=2, showgrid=True, gridcolor='#E5E5E5')
    fig.update_yaxes(title_text='', row=1, col=2, showgrid=False)

    fig.update_xaxes(title_text='', row=2, col=2, tickangle=-45, showgrid=False)
    fig.update_yaxes(title_text='Trade Records', row=2, col=2, showgrid=True, gridcolor='#E5E5E5')

    fig.update_xaxes(title_text='', row=3, col=1, tickangle=-45, showgrid=False)
    fig.update_yaxes(title_text='Trade Records', row=3, col=1, showgrid=True, gridcolor='#E5E5E5')

    fig.update_xaxes(title_text='', row=3, col=2, tickangle=-45, showgrid=False)
    fig.update_yaxes(title_text='Trade Records', row=3, col=2, showgrid=True, gridcolor='#E5E5E5')

    # The summary box is COMPUTED, never written by hand. The hand-written box
    # that stood here until 7 October 2026 still carried the numbers from the
    # 2025-11-12 run that this data file records as truncated: it claimed "2.3
    # million items, 51,000+ records" under panels drawn from 25.7 million items
    # and 133,497 records, and it named the two leading purposes with their
    # labels swapped -- it said Personal 40% and Commercial 38%, while panel (e)
    # draws Commercial ahead of Personal. The three-exploitation-pattern
    # narrative went with it: its per-product item counts cannot be recomputed
    # from this file, which carries record counts per product and no quantities.
    purpose_total = sum(purpose_values)
    lead = ", ".join(f"{lab} {val:,} ({val / purpose_total:.1%})"
                     for lab, val in zip(purpose_labels[:3], purpose_values[:3]))
    summary = (
        f"<b>What this figure sums to.</b> {len(all_species)} wild-origin species, "
        f"{data['total_quantity']:,.0f} items in {data['total_records']:,} trade "
        f"records, 1985-2024. Panels (a) to (c) are measured in items traded and "
        f"panels (d) to (f) count trade records; the two are not interchangeable.<br>"
        f"Leading purposes by record count: {lead}. Panels (d) and (f) sum each "
        f"species' own top five products and exporting countries, so a category in "
        f"no species' top five is absent and every bar there is a lower bound."
    )
    for stale in ("2.3 million", "51,000+", "6x higher"):
        assert stale not in summary, f"stale hand-written figure: {stale}"
    assert f"{data['total_records']:,}" in summary

    fig.add_annotation(
        text=summary,
        xref='paper', yref='paper',
        x=0.5, y=-0.065,
        xanchor='center', yanchor='top',
        showarrow=False,
        font=dict(size=11, family='Arial, sans-serif', color='#333'),
        bgcolor='rgba(205,255,205,0.9)',
        bordercolor='#1F6FB2',
        borderwidth=2,
        borderpad=15,
        align='left'
    )

    # Add data source note
    fig.add_annotation(
        text="<b>Data Source:</b> CITES Trade Database (source='W' wild-origin) • <b>Conservation Status:</b> IUCN Red List (latest) • <b>Period:</b> 1985-2024 (39 years)",
        xref='paper', yref='paper',
        x=0.5, y=-0.145,
        xanchor='center', yanchor='top',
        showarrow=False,
        font=dict(size=10, family='Arial, sans-serif', color='#666'),
        align='center'
    )

    print("✓ Figure created successfully")

    return fig

def main():
    """Generate and save Figure 8"""
    fig = create_figure()

    if fig is None:
        print("\n❌ Failed to create figure")
        return

    # Save to HTML
    output_dir = Path(__file__).parent.parent / 'production'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'figure8_wild_origin_trade.html'

    print(f"\n[4] Saving figure to: {output_file}")
    save_figure(fig, 'figure8_wild_origin_trade', width=1800, height=1700)

    print("\n" + "=" * 80)
    print("FIGURE 8 GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nView figure at: {output_file}")
    print(f"Open in browser: file://{output_file.absolute()}")

if __name__ == '__main__':
    main()
