#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""
Figure 5: IUCN Conservation Status Heatmap Over Time

Heatmap showing the temporal evolution of IUCN Red List status
for Arctic species from 1965-2025.

Data: IUCN Historic Timeline from iucn_historic_timeline.json
"""

import json
from pathlib import Path
import plotly.graph_objects as go
import numpy as np
from figure_output import save_figure

# IUCN Red List colors - enhanced saturation and contrast
IUCN_COLORS = {
    'CR': '#8B0000',  # Critically Endangered - Dark Red
    'EN': '#E25822',  # Endangered - Orange-Red
    'VU': '#F4A300',  # Vulnerable - Orange
    'V': '#F4A300',   # Legacy Vulnerable - Orange
    'NT': '#FFF79A',  # Near Threatened - Light Yellow
    'LC': '#C7E9B4',  # Least Concern - Light Green
    'DD': '#D9D9D9',  # Data Deficient - Light Grey
    'NR': '#F5F5F5',  # Not Recognized (legacy) - Very Light Grey
    'RE': '#000000',  # Regionally Extinct - Black
    'LR/lc': '#C7E9B4',  # Legacy Least Concern
    'LR/cd': '#C7E9B4',  # Legacy Lower Risk/conservation dependent - Light Green
    'LR/nt': '#FFF79A',  # Legacy Near Threatened
    'K': '#D9D9D9',  # Legacy insufficiently known
    'N/A': '#F5F5F5',  # Not assessed
}

# Numeric mapping for the heatmap, DERIVED from the one Red List scale rather
# than written out here.
#
# Deriving it keeps the heatmap on the same ladder as every other number in
# the project. The manuscript reads LR/cd as Near Threatened, on the crosswalk
# it cites, so the heatmap does too; it is the one place a reader can see the
# per-year categories for themselves, so it must rank them as the text does.
#
# Anything the module cannot rank shares one slot, NON_COMPARABLE, between LC
# and NT, which is where DD already sat. That display is deliberate: the cell
# says "a category was recorded here and it does not enter a trajectory",
# which is exactly what the Methods say about those codes.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "ingest"))
import redlist_scale as _rl

NON_COMPARABLE = 1.5
_SHIFT = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}

STATUS_NUMERIC = {
    code: (_SHIFT[_rl.rank(code)] if _rl.rank(code) is not None
           else NON_COMPARABLE)
    for code in ('LC', 'LR/lc', 'LR/cd', 'LR/nt', 'NT', 'VU', 'V', 'EN', 'E',
                 'CR', 'EW', 'EX', 'K', 'T', 'DD', 'RE')
}
# RE keeps a cell of its own. It does not enter a trajectory - it is a regional
# outcome, not a point on the global threat scale - but it IS a recorded
# outcome, and regional-extinction cells are among the most informative cells
# in this figure. Folding it in with "no category
# recorded" would hide them. Above EX, with its own black, because that is what
# it means locally.
STATUS_NUMERIC.update({'RE': 8, 'NR': 0, 'N/A': 0})

# The colour a cell takes must say the same thing as its number. LR/cd ranks
# as Near Threatened, so it takes the Near Threatened colour too.
IUCN_COLORS['LR/cd'] = IUCN_COLORS['LR/nt']

def load_iucn_timeline_data():
    """Load IUCN historic timeline data"""
    data_file = Path(__file__).parent.parent.parent / 'data/processed/iucn_historic_timeline.json'
    with open(data_file, 'r') as f:
        return json.load(f)

# Values that are not a Red List status: a record exists for the year but no
# assessment was made. They map to the "no data" cell and carry no information.
NO_STATUS = {'N/A', 'NA', 'NR', 'Not Assessed', '', None}


def first_real_assessment_year(data, default=1982):
    """Earliest year carrying an actual Red List status (not a 'not assessed' placeholder)."""
    return min(
        (a['year']
         for species in data['species_timelines']
         for scope_data in species['scope_timelines'].values()
         for a in scope_data.get('assessments', [])
         if a['status'] not in NO_STATUS),
        default=default,
    )


# Row labels that must not come from the timeline's own common_name field.
#
# Checked on 7 October 2026 against the deposit's curated common_names table and
# against the paper: four of the 43 labels differ from the curated main English
# name, and three of those four are the figure being RIGHT and the curated name
# being too coarse - the paper says "Atlantic walrus", "beluga whale", and
# deliberately says "common minke whale" because it has to be told apart from
# the Antarctic minke, which is not an Arctic species.
#
# One is wrong in both directions: the timeline calls Rhodiola rosea "Arctic
# Rose", the curated table's main English name is "Roseroot", and "Arctic Rose"
# appears nowhere in the manuscript, which says roseroot nine times. A reader
# matching the figure to the text would not find the row.
LABEL = {"Rhodiola rosea": "Roseroot"}

# The scopes the heatmap draws, which are the scopes the trajectory reads.
SCOPES = ("Global", "Europe")


def _not_in_series():
    """Assessment ids the scope corrections place outside Global and Europe."""
    import csv
    f = Path(__file__).resolve().parents[2] / "species_data/curated/iucn_scope_corrections.csv"
    with open(f, newline="") as fh:
        return {int(r["assessment_id"]) for r in csv.DictReader(fh)
                if r["corrected_scope_description"] != "Europe"}


NOT_IN_SERIES = _not_in_series()


def prepare_heatmap_data(data, start_year=None):
    """Prepare data matrix for heatmap visualization - global and European assessments.

    HISTORY (superseded 21 October 2026, kept because it explains the RE cell):

    It merged every scope until 7 October 2026, with the rule "Global wins for
    the same year". That rule does nothing in the year a species has no global
    assessment, and the corpus has exactly that case 18 times: a 2023 European
    assessment with no global one beside it. Because the heatmap carries the
    last known status forward, those European cells became the RIGHT-HAND EDGE
    of eighteen of the forty-three rows - the cells a reader's eye lands on for
    "where is this species now".

    The result was a figure whose current-status edge was European for 18
    species while every number in the paper is global, and in the worst case it
    inverted a reported result: one species the Results list among the twelve
    IMPROVED (on its global assessments) had a row ending in four cells drawn
    from a European regional-only outcome.

    It was global only from 7 October to 21 October 2026, the scope the
    trajectory was then defined on. On 21 October the lead author included the
    European assessments in the trajectory, so the figure draws both again and
    the defect above no longer applies: the right-hand edge is now the cell the
    trajectory reads. Where a species' latest comparable assessment is
    European, its right-hand edge comes from that assessment, and the caption says the trajectory ends on its latest comparable cell.
    

    start_year defaults to the first year with a real assessment, so the axis begins
    where the status evolution actually begins rather than at a hardcoded literal.
    This was 1982 -- a magic number carried over from an old visualization spec that
    happened to be right: the only pre-1982 records in the corpus are five 1965
    'not assessed' placeholders (Blue, Bowhead, Fin and Humpback Whale, and Polar
    Bear) that the Source Data ships but that carry no status. Deriving the start
    keeps the current axis (1982) while making the choice principled and robust: if a
    real earlier assessment is ever added, the figure follows the data instead of
    silently clipping it. Pass an explicit year only to clip the axis deliberately.
    """
    if start_year is None:
        start_year = first_real_assessment_year(data)
    species_data = {}
    all_years = set()

    # Collect all data from ALL scopes (Global, Europe, etc.)
    for species in data['species_timelines']:
        name = LABEL.get(species['scientific_name'], species['common_name'])
        species_years = {}

        # Global and European, read as one series (the lead author's decision
        # of 21 October 2026, which the trajectory follows). Merging scopes is
        # no longer a defect because the trajectory now reads the same cells;
        # what made it one was a figure merging what the text did not. In a
        # year with both, the higher assessment id stands, as the Methods
        # state. The Mediterranean assessment the scope corrections name is
        # neither and stays out.
        merged = {}
        for scope in SCOPES:
            for assessment in (species['scope_timelines'].get(scope) or {}).get('assessments', []):
                if int(assessment['assessment_id']) in NOT_IN_SERIES:
                    continue
                year = assessment['year']
                if year >= start_year:
                    if year not in merged or assessment['assessment_id'] > merged[year]['assessment_id']:
                        merged[year] = assessment
        for year, assessment in merged.items():
            species_years[year] = assessment['status']
            all_years.add(year)

        # Every species with any global assessment in the window is drawn. The
        # rule was ">= 3 assessments", which silently dropped roseroot - the
        # paper's one plant, and its only global assessment inside the window is
        # 2014 LC - so a 43-species paper carried a figure of 42 and said
        # nothing. A species with one cell is informative: it is the reason that
        # species has no trajectory.
        if species_years:
            species_data[name] = species_years

    # Sort years and species
    years_sorted = sorted(all_years)

    # Create complete year range from start_year to latest year
    if years_sorted:
        complete_years = list(range(start_year, max(years_sorted) + 1))
    else:
        complete_years = []

    # Sort species by taxonomic group and current status
    def get_sort_key(item):
        name, year_data = item
        # Get latest status
        latest_year = max(year_data.keys())
        latest_status = year_data[latest_year]
        status_rank = STATUS_NUMERIC.get(latest_status, 0)

        # Group by type (mammals, birds, fish)
        mammals = ['Whale', 'Bear', 'Walrus', 'Seal', 'Otter', 'Fox', 'Lynx', 'Wolverine', 'Caribou', 'Muskox']
        birds = ['Goose', 'Crane', 'Owl', 'Falcon', 'Eagle', 'Buzzard', 'Curlew', 'Albatross', 'Gull', 'Auklet', 'Murre', 'Eider']
        fish = ['Shark', 'sturgeon', 'Salmon']

        if any(m in name for m in mammals):
            group = 1
        elif any(b in name for b in birds):
            group = 2
        elif any(f in name for f in fish):
            group = 3
        else:
            group = 4

        return (group, -status_rank, name)

    species_sorted = sorted(species_data.items(), key=get_sort_key)
    species_names = [s[0] for s in species_sorted]

    # Create matrix with forward-filled status
    matrix = []
    status_matrix = []  # For hover text

    for species_name in species_names:
        year_data = species_data[species_name]
        row = []
        status_row = []

        # Forward-fill status values
        current_status = None
        current_numeric = None

        for year in complete_years:
            if year in year_data:
                # New assessment - update current status
                current_status = year_data[year]
                current_numeric = STATUS_NUMERIC.get(current_status, 0)

            # Use current status (forward-filled from last assessment)
            if current_status is not None:
                row.append(current_numeric)
                status_row.append(current_status)
            else:
                # No assessment yet for this species
                row.append(None)
                status_row.append('N/A')

        matrix.append(row)
        status_matrix.append(status_row)

    return complete_years, species_names, matrix, status_matrix

def create_figure():
    """Create Figure 5: Status Heatmap"""
    print("Loading IUCN timeline data...")
    data = load_iucn_timeline_data()

    print("Preparing heatmap data...")
    years, species, matrix, status_matrix = prepare_heatmap_data(data)

    print(f"Creating heatmap for {len(species)} species across {len(years)} years...")

    # Create custom colorscale with enhanced contrast
    colorscale = [
        [0.0, '#F5F5F5'],   # No data (very light grey)
        [0.16, '#C7E9B4'],  # LC (light green)
        [0.25, '#D9D9D9'],  # DD (light grey)
        [0.33, '#FFF79A'],  # NT (light yellow)
        [0.5, '#F4A300'],   # VU (orange)
        [0.66, '#E25822'],  # EN (orange-red)
        [0.83, '#8B0000'],  # CR (dark red)
        [1.0, '#000000']    # RE (black)
    ]

    # Create hover text
    hover_text = []
    for i, species_name in enumerate(species):
        hover_row = []
        for j, year in enumerate(years):
            status = status_matrix[i][j]
            status_names = {
                'LC': 'Least Concern',
                'NT': 'Near Threatened',
                'VU': 'Vulnerable',
                'EN': 'Endangered',
                'CR': 'Critically Endangered',
                'DD': 'Data Deficient',
                'RE': 'Regionally Extinct',
                'LR/lc': 'Least Concern',
                'LR/nt': 'Near Threatened',
                'K': 'Data Deficient',
                'N/A': 'Not Assessed'
            }
            status_full = status_names.get(status, status)
            hover_row.append(f"{species_name}<br>Year: {year}<br>Status: {status_full}")
        hover_text.append(hover_row)

    # The status code is drawn in every cell, not only on the colourbar.
    #
    # This palette is the IUCN's own category scale, which the field recognises
    # and which we are not going to substitute. It is also, unavoidably, a
    # red-to-green ramp. Simulated under deuteranopia (Vienot 1999), the closest
    # of the ten category pairs is NT against VU at a CIE76 delta-E of 11.7, with
    # LC/EN at 18.7 and EN/CR at 19.3. No pair falls below delta-E 5, so none is
    # strictly indistinguishable; the ramp compresses rather than collapses, and
    # it compresses hardest between adjacent categories, which is where the
    # distinction has to hold. These figures are recomputed by a document
    # check (not part of the public release) that fails if they and the
    # palette disagree.
    #
    # Hover text does not help: it does not exist in a printed figure, and the
    # manuscript figure is printed. Without a cell label, a reader with the most
    # common form of colour blindness cannot read this figure at all.
    #
    # So the code is drawn in the cell. The palette keeps its disciplinary
    # meaning and stops being the only channel.
    cell_text = [[status_matrix[i][j] if status_matrix[i][j] not in (None, '', 'N/A') else ''
                  for j in range(len(years))] for i in range(len(species))]

    # Create heatmap with better gridlines and spacing
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=years,
        y=species,
        colorscale=colorscale,
        showscale=True,
        text=cell_text,
        texttemplate="%{text}",
        textfont=dict(size=6, color="#111111"),
        hovertext=hover_text,
        hoverinfo='text',
        colorbar=dict(
            title=dict(
                text="IUCN Threat Status",
                side="right",
                font=dict(size=11)
            ),
            tickvals=[1, 1.5, 2, 3, 4, 5, 6],
            ticktext=['LC', 'DD', 'NT', 'VU', 'EN', 'CR', 'RE'],
            tickfont=dict(size=10),
            len=0.6,
            thickness=12,
            x=1.01,
            outlinewidth=1,
            outlinecolor='#333'
        ),
        zmin=0,
        zmax=6,
        xgap=0.5,  # Subtle gap between year columns
        ygap=1.5   # Subtle gap between species rows
    ))

    # Update layout with improved spacing and aesthetics
    fig.update_layout(
        title={
            'text': "",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'family': 'Arial, sans-serif'}
        },
        xaxis=dict(
            title='Year',
            tickmode='linear',
            tick0=years[0],
            dtick=2,  # Show every 2 years for better readability
            tickangle=45,
            title_font=dict(size=13),
            tickfont=dict(size=9),
            showgrid=False,
            side='bottom'
        ),
        yaxis=dict(
            title='',
            title_font=dict(size=13),
            tickfont=dict(size=9),
            showgrid=False,
            autorange='reversed'
        ),
        height=max(800, len(species) * 22),  # Slightly taller rows
        width=1400,
        font=dict(family='Arial, sans-serif', size=10),
        plot_bgcolor='#f8f8f8',  # Light grey background
        paper_bgcolor='white',
        margin=dict(t=80, b=100, l=250, r=120)
    )

    return fig, {
        'num_species': len(species),
        'num_years': len(years),
        'year_range': (min(years), max(years)),
        'species_list': species
    }

def main():
    print("=" * 70)
    print("FIGURE 5: IUCN STATUS HEATMAP OVER TIME")
    print("=" * 70)

    fig, stats = create_figure()

    output_dir = Path(__file__).parent.parent / 'production'
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / 'figure5_status_heatmap.html'

    print(f"\nSaving to: {output_file}")

    # Save HTML with CDN
    save_figure(fig, 'figure5_status_heatmap', width=1600, height=1800)

    print(f"✅ Saved successfully!")
    print(f"\nFile size: {output_file.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 70)
    print("KEY STATISTICS:")
    print("=" * 70)
    print(f"Species included: {stats['num_species']}")
    print(f"Years covered: {stats['num_years']} ({stats['year_range'][0]}-{stats['year_range'][1]})")
    print(f"\nSpecies groups:")

    # Count by group
    mammals = sum(1 for s in stats['species_list'] if any(m in s for m in ['Whale', 'Bear', 'Walrus', 'Seal', 'Otter', 'Fox', 'Lynx', 'Wolverine', 'Caribou', 'Muskox']))
    birds = sum(1 for s in stats['species_list'] if any(b in s for b in ['Goose', 'Crane', 'Owl', 'Falcon', 'Eagle', 'Buzzard', 'Curlew', 'Albatross', 'Gull', 'Auklet', 'Murre', 'Eider']))
    fish = sum(1 for s in stats['species_list'] if any(f in s for f in ['Shark', 'sturgeon', 'Salmon']))

    print(f"  Mammals: {mammals}")
    print(f"  Birds: {birds}")
    print(f"  Fish: {fish}")

    print(f"\n\nOpen with:")
    print(f"  open {output_file}")
    print("=" * 70)

if __name__ == '__main__':
    main()
