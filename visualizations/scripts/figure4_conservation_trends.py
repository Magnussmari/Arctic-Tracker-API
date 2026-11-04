#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""
Figure 4: IUCN Conservation Status Trends for Arctic Species (1965-2025)

Shows the temporal evolution of conservation assessments and status changes
for Arctic species over a 60-year period.

Data: IUCN Historic Timeline from iucn_historic_timeline.json
"""

import json
from pathlib import Path
from collections import defaultdict
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from figure_output import save_figure

# IUCN Red List standard colors
IUCN_COLORS = {
    'CR': '#D81E05',  # Critically Endangered
    'EN': '#FC7F3F',  # Endangered
    'VU': '#F9E814',  # Vulnerable
    'NT': '#CCE226',  # Near Threatened
    'LC': '#60C659',  # Least Concern
    'DD': '#D1D1C6',  # Data Deficient
    'NR': '#E8E8E8',  # Not Recognized (legacy)
    'RE': '#000000',  # Regionally Extinct
}

def load_iucn_timeline_data():
    """Load IUCN historic timeline data"""
    data_file = Path(__file__).parent.parent.parent / 'data/processed/iucn_historic_timeline.json'
    with open(data_file, 'r') as f:
        return json.load(f)

def _not_in_series():
    """Assessment ids the scope corrections place outside Global and Europe."""
    import csv
    f = Path(__file__).resolve().parents[2] / "species_data/curated/iucn_scope_corrections.csv"
    with open(f, newline="") as fh:
        return {int(r["assessment_id"]) for r in csv.DictReader(fh)
                if r["corrected_scope_description"] != "Europe"}


NOT_IN_SERIES = _not_in_series()


def analyze_status_changes(data):
    """Analyze IUCN status changes for each species"""
    # D10 (2026-08-11): the scale lives in ingest/redlist_scale.py, not here.
    #
    # This function used to carry its own, in which 'K' (Insufficiently Known)
    # scored 1, the same as Least Concern. Four other scripts let the same
    # category fall to 0, below Least Concern. The two disagreed on the
    # direction of change for 30 of 43 species, and neither reproduced the
    # published tally.
    #
    # It also counted a species with a single assessment as "Unchanged", which
    # is not a trajectory at all: one point is not a line. Those species are
    # now excluded and reported.
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "ingest"))
    import redlist_scale as rl

    uplisted = 0  # Moved to more threatened category
    downlisted = 0  # Moved to less threatened category
    unchanged = 0  # No change in status

    species_details = []

    excluded = 0
    excluded_details = []

    for species in data['species_timelines']:
        name = species['common_name']
        # Global and European assessments as one series (the lead author's
        # decision of 21 October 2026), ordered by year and then assessment id
        # so the later publication stands last in a tied year. The one
        # Mediterranean assessment the scope corrections name stays out.
        merged = [a for scope in ('Global', 'Europe')
                  for a in (species['scope_timelines'].get(scope) or {}).get('assessments', [])
                  if int(a['assessment_id']) not in NOT_IN_SERIES
                  and 1982 <= a['year'] <= 2025]
        for scope_name, scope_data in [('Global+Europe', {'assessments': sorted(
                merged, key=lambda a: (a['year'], int(a['assessment_id'])))})]:
            if scope_data['assessments']:
                assessments = scope_data['assessments']

                # Comparable assessments only: a trajectory needs two ends that
                # mean the same kind of thing.
                valid_assessments = [a for a in assessments if rl.comparable(a['status'])]

                if len(valid_assessments) >= 2:
                    first = valid_assessments[0]
                    last = valid_assessments[-1]
                    change = rl.classify(first['status'], last['status'])

                    if change == 'deteriorated':
                        uplisted += 1
                        change_type = 'Uplisted'
                    elif change == 'improved':
                        downlisted += 1
                        change_type = 'Downlisted'
                    else:
                        unchanged += 1
                        change_type = 'Unchanged'

                    species_details.append({
                        'name': name,
                        'first_status': first['status'],
                        'last_status': last['status'],
                        'change_type': change_type,
                        'current_status': last['status']
                    })
                else:
                    excluded += 1
                    raw_first = assessments[0]['status'] if assessments else None
                    excluded_details.append({
                        'name': name,
                        'first_status': raw_first,
                        'reason': rl.reason_excluded(raw_first) if not valid_assessments
                                  else 'only one comparable assessment'
                    })


    return {
        'uplisted': uplisted,
        'downlisted': downlisted,
        'unchanged': unchanged,
        'excluded': excluded,
        'species_details': species_details,
        'excluded_details': excluded_details
    }

def create_figure():
    """Create Figure 4: Conservation Trends"""
    print("Loading IUCN timeline data...")
    data = load_iucn_timeline_data()

    summary = data['summary']
    print(f"Analyzing {summary['total_species_analyzed']} species...")
    print(f"Assessment period: {summary['assessment_year_range']['earliest']}-{summary['assessment_year_range']['latest']}")

    # Analyze status changes
    change_analysis = analyze_status_changes(data)

    # Calculate percentages
    total_assessed = change_analysis['uplisted'] + change_analysis['downlisted'] + change_analysis['unchanged']
    if total_assessed > 0:
        uplist_pct = (change_analysis['uplisted'] / total_assessed) * 100
        downlist_pct = (change_analysis['downlisted'] / total_assessed) * 100
        unchanged_pct = (change_analysis['unchanged'] / total_assessed) * 100
    else:
        uplist_pct = downlist_pct = unchanged_pct = 0

    # Get current status distribution
    current_status_counts = defaultdict(int)
    for sp in change_analysis['species_details']:
        current_status_counts[sp['current_status']] += 1

    # Create figure with subplots
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=(
            '<b>(a)</b> Post-listing trajectory, species',
            f'<b>(b)</b> Latest comparable category, {total_assessed} species',
            '<b>(c)</b> Post-listing trajectory, share'
        ),
        horizontal_spacing=0.12
    )

    # Clean panel title styling
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(size=13, family='Arial, sans-serif')

    # Panel A: Status change categories (Uplisted, Unchanged, Downlisted)
    # The paper calls these deteriorated / unchanged / improved, and this figure
    # called them "Uplisted (Stricter)" and "Downlisted (Relaxed)". Three
    # problems with that, all visible only by looking at the drawn figure:
    # the vocabulary is not the paper's, so a reader cannot match bar to
    # sentence; "Uplisted" and "Stricter" both sound like a stronger protection
    # while the bar is red and means the species got worse; and "Relaxed" sounds
    # like a weakening while that bar is the good news. A reader could take the
    # figure exactly backwards.
    change_labels = ['Deteriorated', 'Unchanged', 'Improved']
    change_values = [
        change_analysis['uplisted'],
        change_analysis['unchanged'],
        change_analysis['downlisted']
    ]
    change_colors = ['#D81E05', '#CCE226', '#60C659']  # Red for worse, yellow for stable, green for better

    fig.add_trace(
        go.Bar(
            x=change_labels,
            y=change_values,
            marker=dict(color=change_colors),
            text=change_values,
            textposition='auto',
            hovertemplate='%{x}<br>Species count: %{y}<extra></extra>'
        ),
        row=1, col=1
    )

    # Panel B: Current status distribution
    status_order = ['LC', 'NT', 'VU', 'EN', 'CR', 'DD', 'RE']
    status_names = {
        'LC': 'Least Concern',
        'NT': 'Near Threatened',
        'VU': 'Vulnerable',
        'EN': 'Endangered',
        'CR': 'Critically Endangered',
        'DD': 'Data Deficient',
        'RE': 'Regionally Extinct'
    }

    status_labels = []
    status_values = []
    status_colors = []

    for status in status_order:
        if current_status_counts[status] > 0:
            status_labels.append(status_names.get(status, status))
            status_values.append(current_status_counts[status])
            status_colors.append(IUCN_COLORS.get(status, '#999'))

    fig.add_trace(
        go.Bar(
            x=status_labels,
            y=status_values,
            marker=dict(color=status_colors),
            text=status_values,
            textposition='auto',
            hovertemplate='%{x}<br>Species count: %{y}<extra></extra>'
        ),
        row=1, col=2
    )

    # Panel C: Percentages
    pct_labels = ['Deteriorated', 'Unchanged', 'Improved']
    pct_values = [uplist_pct, unchanged_pct, downlist_pct]
    pct_colors = ['#D81E05', '#CCE226', '#60C659']

    fig.add_trace(
        go.Bar(
            x=pct_labels,
            y=pct_values,
            marker=dict(color=pct_colors),
            text=[f"{v:.1f}%" for v in pct_values],
            textposition='auto',
            hovertemplate='%{x}<br>Percentage: %{y:.1f}%<extra></extra>'
        ),
        row=1, col=3
    )

    # Update layout
    fig.update_layout(
        title={
            'text': "",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'family': 'Arial, sans-serif'}
        },
        showlegend=False,
        height=600,
        width=1400,
        font=dict(family='Arial, sans-serif', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=100, b=80, l=80, r=80)
    )

    # Update axes
    fig.update_xaxes(
        title_text="",
        title_font=dict(size=13),
        row=1, col=1,
        showgrid=False
    )
    fig.update_yaxes(
        title_text="Number of Species",
        title_font=dict(size=13),
        row=1, col=1,
        showgrid=True,
        gridcolor='#E5E5E5'
    )

    fig.update_xaxes(
        title_text="",
        title_font=dict(size=13),
        row=1, col=2,
        showgrid=False
    )
    fig.update_yaxes(
        title_text="Number of Species",
        title_font=dict(size=13),
        row=1, col=2,
        showgrid=True,
        gridcolor='#E5E5E5'
    )

    fig.update_xaxes(
        title_text="",
        title_font=dict(size=13),
        row=1, col=3,
        showgrid=False
    )
    fig.update_yaxes(
        title_text="Percentage (%)",
        title_font=dict(size=13),
        row=1, col=3,
        showgrid=True,
        gridcolor='#E5E5E5'
    )

    return fig, {
        'total_species': summary['total_species_analyzed'],
        'year_range': summary['assessment_year_range'],
        'uplisted': change_analysis['uplisted'],
        'downlisted': change_analysis['downlisted'],
        'unchanged': change_analysis['unchanged'],
        'uplist_pct': uplist_pct,
        'downlist_pct': downlist_pct,
        'unchanged_pct': unchanged_pct,
        'species_details': change_analysis['species_details']
    }

def main():
    print("=" * 70)
    print("FIGURE 4: IUCN CONSERVATION STATUS CHANGES")
    print("=" * 70)

    fig, stats = create_figure()

    output_dir = Path(__file__).parent.parent / 'production'
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / 'figure4_conservation_trends.html'

    print(f"\nSaving to: {output_file}")

    # Save HTML with CDN
    save_figure(fig, 'figure4_conservation_trends', width=1600, height=1200)

    print(f"✅ Saved successfully!")
    print(f"\nFile size: {output_file.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 70)
    print("KEY STATISTICS:")
    print("=" * 70)
    print(f"Total species analyzed: {stats['total_species']}")
    print(f"Assessment period: {stats['year_range']['earliest']}-{stats['year_range']['latest']}")

    print(f"\nStatus Changes (Absolute):")
    print(f"  Uplisted (Stricter): {stats['uplisted']} species")
    print(f"  Unchanged: {stats['unchanged']} species")
    print(f"  Downlisted (Relaxed): {stats['downlisted']} species")

    print(f"\nStatus Changes (Percentages):")
    print(f"  Uplisted (Stricter): {stats['uplist_pct']:.1f}%")
    print(f"  Unchanged: {stats['unchanged_pct']:.1f}%")
    print(f"  Downlisted (Relaxed): {stats['downlist_pct']:.1f}%")

    print(f"\nExample species by change type:")
    uplisted_examples = [sp for sp in stats['species_details'] if sp['change_type'] == 'Uplisted'][:3]
    downlisted_examples = [sp for sp in stats['species_details'] if sp['change_type'] == 'Downlisted'][:3]

    if uplisted_examples:
        print(f"\n  Uplisted (worse conservation status):")
        for sp in uplisted_examples:
            print(f"    - {sp['name']}: {sp['first_status']} → {sp['last_status']}")

    if downlisted_examples:
        print(f"\n  Downlisted (improved conservation status):")
        for sp in downlisted_examples:
            print(f"    - {sp['name']}: {sp['first_status']} → {sp['last_status']}")

    print(f"\n\nOpen with:")
    print(f"  open {output_file}")
    print("=" * 70)

if __name__ == '__main__':
    main()
