#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""
Figure 2: CITES-Listed Arctic Species Trade Patterns
(Proxy for enforcement concern - based on documented trade records)

Note: This visualization uses CITES legal trade records as a proxy for
species facing enforcement challenges. True seizure data would require
additional CITES purpose code filtering or separate enforcement databases.

DATA PERIOD NOTE: Source data includes records through 2024. The aggregate
statistics in the JSON file represent the full period without year-by-year
breakdowns. Frontend trackers filtering to 2023 will show slightly lower
counts (e.g., Siberian sturgeon: 189,116 total vs 179,435 through 2023).

Data Period: 1975-2024 (50 years)
"""

import csv
import json
from collections import Counter
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from figure_output import save_figure

# IUCN Colors (standardized)
IUCN_COLORS = {
    'CR': '#D81E05', 'EN': '#FC7F3F', 'VU': '#F9E814',
    'NT': '#CCE226', 'LC': '#60C659', 'DD': '#D1D1C6',
}

# CITES purpose code descriptions
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
    'Z': 'Zoo',
    'N': 'Reintroduction',
    'G': 'Botanic garden',
}
# Every code that appears in the corpus must be named here, or a bar carries a
# bare letter. Checked against the records on 7 October 2026: T, P, H, S, blank,
# B, Q, E, Z, N, M and L.


# The deposited corpus of record. Panels (b) and (c) are computed from it and
# not from the per-species export, because the export carries one CURRENT
# appendix and one MODAL purpose per species, and summing a species' whole
# record total into those two buckets answers a different question from the one
# the panel titles ask. Measured on 7 October 2026, the difference was not
# cosmetic: panel (c) read "Commercial 405,381" where the corpus holds 329,770
# commercial records, which is the 67% the paper reports in Section 4.5, and
# panel (b) moved about 4,000 records between Appendix I and II against the
# shares the deposit verifies as C04 to C06.
TRADE_RECORDS = (Path(__file__).parent.parent.parent
                 / 'deposit' / 'tables' / 'cites_trade_records.csv')


def record_level_distributions():
    """{appendix: records}, {purpose code: records} straight off the records."""
    appendix, purpose = Counter(), Counter()
    with open(TRADE_RECORDS, newline='') as fh:
        for row in csv.DictReader(fh):
            appendix[row['appendix']] += 1
            purpose[row['purpose']] += 1
    return appendix, purpose


def load_data():
    """Load CITES effectiveness data"""
    data_file = Path(__file__).parent.parent.parent / 'data/raw/1_DATA_cites_effectiveness.json'
    with open(data_file, 'r') as f:
        return json.load(f)

def prepare_data(data):
    """Extract and organize species data"""
    species_list = []

    for sp in data['species_analyses']:
        species_list.append({
            'name': sp.get('common_name', 'Unknown'),
            'scientific': sp.get('scientific_name', ''),
            'total_trade': sp.get('trade_records_count', 0),
            'wild_origin': sp.get('wild_origin_count', 0),
            'iucn': sp.get('iucn_status', 'LC'),
            'appendix': sp.get('cites_appendix', 'Unknown'),
            'purpose': sp.get('most_recorded_trade_use', 'Unknown'),
            'trend': sp.get('trade_trend', 'Unknown')
        })

    return species_list

def create_figure():
    """Create 4-panel enforcement visualization"""
    print("Loading data...")
    data = load_data()
    species_list = prepare_data(data)

    # Sort by total trade and get top 10
    species_list.sort(key=lambda x: x['total_trade'], reverse=True)
    top10 = species_list[:10]

    print(f"Creating figure with top 10 species...")

    # Create subplot layout: 2x2 grid
    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{'type': 'bar'}, {'type': 'bar'}],
               [{'colspan': 2}, None]],
        subplot_titles=(
            '<b>(a)</b> Top 10 Most-Traded Species',
            '<b>(b)</b> Trade by CITES Appendix',
            '<b>(c)</b> Trade by Purpose Category'
        ),
        # Panel (c) now carries twelve categories and needs the height; the
        # default split left a blank band across the middle of the figure.
        row_heights=[0.44, 0.56],
        vertical_spacing=0.11,
        horizontal_spacing=0.12
    )

    # Clean panel title styling matching Figure 3
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(size=13, family='Arial, sans-serif')

    # Panel A: Top 10 species by trade volume (color by IUCN status)
    names = [s['name'] for s in top10]
    trades = [s['total_trade'] for s in top10]
    colors = [IUCN_COLORS.get(s['iucn'], '#999') for s in top10]

    fig.add_trace(
        go.Bar(
            y=names[::-1],
            x=trades[::-1],
            orientation='h',
            marker=dict(color=colors[::-1]),
            name='Trade records',
            text=[f"{t:,}" for t in trades[::-1]],
            textposition='auto',
        ),
        row=1, col=1
    )

    # Panel B: Distribution by CITES Appendix
    appendix_rec, purpose_rec = record_level_distributions()
    appendix_trade = dict(appendix_rec)

    # 'N' is a record whose shipment predates the species' listing; it is a real
    # category of the corpus and is drawn rather than dropped.
    APPENDIX_LABEL = {'I': 'I', 'II': 'II', 'III': 'III',
                      'N': 'N (not listed when shipped)'}
    appendix_order = ['I', 'II', 'III', 'N']
    apps = [APPENDIX_LABEL[a] for a in appendix_order if a in appendix_trade]
    values = [appendix_trade[a] for a in appendix_order if a in appendix_trade]

    fig.add_trace(
        go.Bar(
            x=apps,
            y=values,
            marker=dict(color='#C44536'),  # Red for enforcement
            name='Trade volume',
            text=[f"{v:,}" for v in values],
            textposition='auto',
        ),
        row=1, col=2
    )

    # Panel C: Trade purpose categories (bottom, full width)
    # Every purpose code present in the corpus, blank included. Nothing is
    # truncated: a code left out of the panel is a code the reader cannot see
    # was small rather than absent.
    purpose_trade = {PURPOSE_CODES.get(code) or (code or 'Unspecified'): n
                     for code, n in purpose_rec.items()}
    purposes = sorted(purpose_trade.items(), key=lambda x: x[1], reverse=True)
    p_names = [p[0] for p in purposes]
    p_values = [p[1] for p in purposes]

    purpose_colors = ['#8B4513', '#A0522D', '#CD853F', '#DEB887', '#F5DEB3',
                      '#FFE4B5', '#EED9C4', '#E8D3BC', '#E2CDB4', '#DCC7AC',
                      '#D6C1A4', '#D0BB9C']

    fig.add_trace(
        go.Bar(
            x=p_names,
            y=p_values,
            marker=dict(color=purpose_colors[:len(p_names)]),
            name='Purpose',
            text=[f"{v:,}" for v in p_values],
            textposition='auto',
        ),
        row=2, col=1
    )

    # Update layout - matching Figure 3 style
    total_trade_all = sum(s['total_trade'] for s in species_list)
    fig.update_layout(
        title={
            # NO FIGURE NUMBER IN THE ARTWORK: this read "Figure 2", the
            # pipeline id, while the manuscript prints it as Figure 5. The
            # binding lives in visualizations/provenance/figure_provenance.json.
            'text': "<b>Arctic Species Trade Patterns (1975-2024)</b><br>" +
                    f"<span style='font-size:11pt; color:#555;'>Trade volume, CITES regulation, and usage patterns | {total_trade_all:,} trade records</span>",
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

    # Update axes - matching Figure 3 style
    fig.update_xaxes(title_text="Total Trade Records", title_font=dict(size=13), row=1, col=1, showgrid=True, gridcolor='#E5E5E5')
    fig.update_xaxes(title_text="CITES Appendix", title_font=dict(size=13), row=1, col=2, showgrid=False)
    fig.update_xaxes(title_text="Trade Purpose", title_font=dict(size=13), row=2, col=1, showgrid=False)

    fig.update_yaxes(title_text="", row=1, col=1, showgrid=True, gridcolor='#E5E5E5')
    fig.update_yaxes(title_text="Trade Records", title_font=dict(size=13), row=1, col=2, showgrid=True, gridcolor='#E5E5E5')
    fig.update_yaxes(title_text="Trade Records", title_font=dict(size=13), row=2, col=1, showgrid=True, gridcolor='#E5E5E5')

    # The panels must agree with the paper. C04-C06 give the appendix shares and
    # Section 4.5 gives 67% commercial; if either drifts, this figure stops.
    n = sum(appendix_trade.values())
    if n != sum(purpose_trade.values()) or n != total_trade_all:
        raise SystemExit(f"panel totals disagree: appendix {n}, purpose "
                         f"{sum(purpose_trade.values())}, species {total_trade_all}")
    shares = {k: round(100 * v / n, 2) for k, v in appendix_trade.items()}
    if [shares.get(k) for k in ('I', 'II', 'III')] != [27.34, 67.34, 5.32]:
        raise SystemExit(f"appendix shares are {shares}, not C04-C06")
    commercial = round(100 * purpose_trade['Commercial'] / n, 1)
    if commercial != 67.0:
        raise SystemExit(f"commercial share is {commercial}%, not the 67% in 4.5")

    return fig, top10, appendix_trade, purpose_trade

def main():
    print("=" * 60)
    print("FIGURE 2: TRADE PATTERNS & ENFORCEMENT CONCERN")
    print("=" * 60)

    fig, top10, appendix_dist, purpose_dist = create_figure()

    # Create output directory
    output_dir = Path(__file__).parent.parent / 'production'
    output_dir.mkdir(exist_ok=True)

    # Save HTML
    output_file = output_dir / 'figure2_trade_enforcement.html'
    print(f"\nSaving to: {output_file}")

    save_figure(fig, 'figure2_trade_enforcement', width=1600, height=1200)

    print(f"✅ Saved successfully!")
    print(f"\nFile size: {output_file.stat().st_size / 1024:.1f} KB")

    # Print statistics
    print("\n" + "=" * 60)
    print("KEY STATISTICS:")
    print("=" * 60)
    print("\nTop 10 Most-Traded Species:")
    for i, sp in enumerate(top10, 1):
        print(f"  {i}. {sp['name']}: {sp['total_trade']:,} records ({sp['iucn']})")

    print("\nTrade by CITES Appendix:")
    for app, count in sorted(appendix_dist.items()):
        print(f"  Appendix {app}: {count:,} records")

    print("\nTrade by Purpose:")
    for purpose, count in sorted(purpose_dist.items(), key=lambda x: x[1], reverse=True):
        print(f"  {purpose}: {count:,} records")

    print("\n" + "=" * 60)
    print(f"\nOpen with:")
    print(f"  open {output_file}")
    print("=" * 60)

if __name__ == '__main__':
    main()
