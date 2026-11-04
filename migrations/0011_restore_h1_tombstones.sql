-- 0011_restore_h1_tombstones.sql  (STAGED — DO NOT RUN ON PROD UNREHEARSED)
-- @orchestrator Magnus Smárason | smarason.is  @created 2026-07-27
-- Restores the 7 H1-deleted wrong-species bindings as TOMBSTONED evidence
-- (binding_status='rejected'), so the audit trail is queryable instead of gone.
-- Generated correct-by-construction from the H1 pre-repair snapshots + audit verdicts.
-- Requires 0010 (status column + reference_candidates) applied first.
BEGIN;

-- Acipenser baerii: statistics methods paper (outlier-prone distributions) — not sturgeon
INSERT INTO arctic.references (id, source_id, authors, year, title, journal, doi, full_citation)
VALUES ('109aab6f-faf7-478a-b968-61810ad92a6f', 'Restriction_of_range_and_correlation_in_outlier-pr_2000_3', 'Zimmerman, D., Williams, R.', 2000, 'Restriction of range and correlation in outlier-prone distributions', 'Applied Psychological Measurement', '10.1177/01466210022031741', 'Zimmerman, D. and Williams, R. (2000). Restriction of range and correlation in outlier-prone distributions. Applied Psychological Measurement, 24(3), 267-280. https://doi.org/10.1177/01466210022031741')
ON CONFLICT (id) DO NOTHING;
INSERT INTO arctic.reference_candidates
  (species_id, profile_id, reference_id, candidate_doi, candidate_title,
   gate_method, gate_verdict, binding_status, gate_reason)
SELECT p.species_id, '3be5ce62-7b9a-4ed1-b14a-499378b23c57', '109aab6f-faf7-478a-b968-61810ad92a6f', '10.1177/01466210022031741', 'Restriction of range and correlation in outlier-prone distributions',
       'incident-audit', 'MISMATCH', 'rejected', 'statistics methods paper (outlier-prone distributions) — not sturgeon'
  FROM arctic.conservation_profiles p WHERE p.id = '3be5ce62-7b9a-4ed1-b14a-499378b23c57'
ON CONFLICT DO NOTHING;

-- Acipenser baerii: red panda in Nepal — not sturgeon (the SPEC-flagged case)
INSERT INTO arctic.references (id, source_id, authors, year, title, journal, doi, full_citation)
VALUES ('e36e74de-6d74-4cf5-b4af-fb0320999af4', 'Distribution_and_habitat_preference_of_red_panda_(_2014_0', 'Bhatta, M., Shah, K., Devkota, B., Paudel, R., Panthi, S.', 2014, 'Distribution and habitat preference of red panda (<i>ailurus fulgens fulgens</i>) in jumla district, nepal', 'Open Journal of Ecology', '10.4236/oje.2014.415082', 'Bhatta, M., Shah, K., Devkota, B., Paudel, R., & Panthi, S. (2014). Distribution and habitat preference of red panda (<i>ailurus fulgens fulgens</i>) in jumla district, nepal. Open Journal of Ecology, 04(15), 989-1001. https://doi.org/10.4236/oje.2014.415082')
ON CONFLICT (id) DO NOTHING;
INSERT INTO arctic.reference_candidates
  (species_id, profile_id, reference_id, candidate_doi, candidate_title,
   gate_method, gate_verdict, binding_status, gate_reason)
SELECT p.species_id, '3be5ce62-7b9a-4ed1-b14a-499378b23c57', 'e36e74de-6d74-4cf5-b4af-fb0320999af4', '10.4236/oje.2014.415082', 'Distribution and habitat preference of red panda (<i>ailurus fulgens fulgens</i>) in jumla district, nepal',
       'incident-audit', 'MISMATCH', 'rejected', 'red panda in Nepal — not sturgeon (the SPEC-flagged case)'
  FROM arctic.conservation_profiles p WHERE p.id = '3be5ce62-7b9a-4ed1-b14a-499378b23c57'
ON CONFLICT DO NOTHING;

-- Acipenser baerii: invasive plants in Spain — not sturgeon
INSERT INTO arctic.references (id, source_id, authors, year, title, journal, doi, full_citation)
VALUES ('77690837-a6e4-4701-95f7-1e4b4ede70d7', 'Potential_distribution_range_of_invasive_plant_spe_2012_1', 'Vilà, M., Gassó, N., Thuiller, W., Pino, J.', 2012, 'Potential distribution range of invasive plant species in spain', 'Neobiota', '10.3897/neobiota.12.2341', 'Vilà, M., Gassó, N., Thuiller, W., & Pino, J. (2012). Potential distribution range of invasive plant species in spain. Neobiota, 12, 25-40. https://doi.org/10.3897/neobiota.12.2341')
ON CONFLICT (id) DO NOTHING;
INSERT INTO arctic.reference_candidates
  (species_id, profile_id, reference_id, candidate_doi, candidate_title,
   gate_method, gate_verdict, binding_status, gate_reason)
SELECT p.species_id, '3be5ce62-7b9a-4ed1-b14a-499378b23c57', '77690837-a6e4-4701-95f7-1e4b4ede70d7', '10.3897/neobiota.12.2341', 'Potential distribution range of invasive plant species in spain',
       'incident-audit', 'MISMATCH', 'rejected', 'invasive plants in Spain — not sturgeon'
  FROM arctic.conservation_profiles p WHERE p.id = '3be5ce62-7b9a-4ed1-b14a-499378b23c57'
ON CONFLICT DO NOTHING;

-- Acipenser baerii: deer in Great Britain — not sturgeon
INSERT INTO arctic.references (id, source_id, authors, year, title, journal, doi, full_citation)
VALUES ('798c44ee-f40a-4afc-b663-814e5d445090', 'Expanding_ranges_of_wild_and_feral_deer_in_great_b_2005_2', 'Ward, A.', 2005, 'Expanding ranges of wild and feral deer in great britain', 'Mammal Review', '10.1111/j.1365-2907.2005.00060.x', 'Ward, A. (2005). Expanding ranges of wild and feral deer in great britain. Mammal Review, 35(2), 165-173. https://doi.org/10.1111/j.1365-2907.2005.00060.x')
ON CONFLICT (id) DO NOTHING;
INSERT INTO arctic.reference_candidates
  (species_id, profile_id, reference_id, candidate_doi, candidate_title,
   gate_method, gate_verdict, binding_status, gate_reason)
SELECT p.species_id, '3be5ce62-7b9a-4ed1-b14a-499378b23c57', '798c44ee-f40a-4afc-b663-814e5d445090', '10.1111/j.1365-2907.2005.00060.x', 'Expanding ranges of wild and feral deer in great britain',
       'incident-audit', 'MISMATCH', 'rejected', 'deer in Great Britain — not sturgeon'
  FROM arctic.conservation_profiles p WHERE p.id = '3be5ce62-7b9a-4ed1-b14a-499378b23c57'
ON CONFLICT DO NOTHING;

-- Falco rusticolus: US state SGCN landscape conservation — not gyrfalcon (borderline, Tom to confirm)
INSERT INTO arctic.references (id, source_id, authors, year, title, journal, doi, full_citation)
VALUES ('175aca3f-cc57-454a-adac-b7d31fd0cbbe', 'A_landscape_conservation_perspective_of_state_spec_2024_0', 'Hamilton, H., Rapacciuolo, G., Kanter, J., Jones‐Farrand, D., Young, B.', 2024, 'A landscape conservation perspective of state species of greatest conservation need', 'Conservation Science and Practice', '10.1111/csp2.13223', 'Hamilton, H., Rapacciuolo, G., Kanter, J., Jones‐Farrand, D., & Young, B. (2024). A landscape conservation perspective of state species of greatest conservation need. Conservation Science and Practice, 6(10). https://doi.org/10.1111/csp2.13223')
ON CONFLICT (id) DO NOTHING;
INSERT INTO arctic.reference_candidates
  (species_id, profile_id, reference_id, candidate_doi, candidate_title,
   gate_method, gate_verdict, binding_status, gate_reason)
SELECT p.species_id, '8350f089-a800-430f-b698-a64fa98f399e', '175aca3f-cc57-454a-adac-b7d31fd0cbbe', '10.1111/csp2.13223', 'A landscape conservation perspective of state species of greatest conservation need',
       'incident-audit', 'MISMATCH', 'rejected', 'US state SGCN landscape conservation — not gyrfalcon (borderline, Tom to confirm)'
  FROM arctic.conservation_profiles p WHERE p.id = '8350f089-a800-430f-b698-a64fa98f399e'
ON CONFLICT DO NOTHING;

-- Falco rusticolus: tricolored blackbird colony size — not gyrfalcon
INSERT INTO arctic.references (id, source_id, authors, year, title, journal, doi, full_citation)
VALUES ('85317268-72c1-4c99-8fb3-05cb58b79c32', 'Trends_in_tricolored_blackbird_colony_size:_2008_t_2019_2', 'Meehan, T., Arthur, S., Michel, N., Wilsey, C., Langham, G.', 2019, 'Trends in tricolored blackbird colony size: 2008 through 2017', 'Journal of Wildlife Management', '10.1002/jwmg.21664', 'Meehan, T., Arthur, S., Michel, N., Wilsey, C., & Langham, G. (2019). Trends in tricolored blackbird colony size: 2008 through 2017. Journal of Wildlife Management, 83(5), 1237-1243. https://doi.org/10.1002/jwmg.21664')
ON CONFLICT (id) DO NOTHING;
INSERT INTO arctic.reference_candidates
  (species_id, profile_id, reference_id, candidate_doi, candidate_title,
   gate_method, gate_verdict, binding_status, gate_reason)
SELECT p.species_id, '8350f089-a800-430f-b698-a64fa98f399e', '85317268-72c1-4c99-8fb3-05cb58b79c32', '10.1002/jwmg.21664', 'Trends in tricolored blackbird colony size: 2008 through 2017',
       'incident-audit', 'MISMATCH', 'rejected', 'tricolored blackbird colony size — not gyrfalcon'
  FROM arctic.conservation_profiles p WHERE p.id = '8350f089-a800-430f-b698-a64fa98f399e'
ON CONFLICT DO NOTHING;

-- Falco rusticolus: common nightingale population methods — not gyrfalcon
INSERT INTO arctic.references (id, source_id, authors, year, title, journal, doi, full_citation)
VALUES ('541deded-ef79-4dc7-8016-7dac6a01486c', 'Estimating_national_population_sizes:_methodologic_2018_1', 'Hewson, C., Miller, M., Johnston, A., Conway, G., Saunders, R., Marchant, J., Fuller, R.', 2018, 'Estimating national population sizes: methodological challenges and applications illustrated in the common nightingale, a declining songbird in the uk', 'Journal of Applied Ecology', '10.1111/1365-2664.13120', 'Hewson, C., Miller, M., Johnston, A., Conway, G., Saunders, R., Marchant, J., … & Fuller, R. (2018). Estimating national population sizes: methodological challenges and applications illustrated in the common nightingale, a declining songbird in the uk. Journal of Applied Ecology, 55(4), 2008-2018. https://doi.org/10.1111/1365-2664.13120')
ON CONFLICT (id) DO NOTHING;
INSERT INTO arctic.reference_candidates
  (species_id, profile_id, reference_id, candidate_doi, candidate_title,
   gate_method, gate_verdict, binding_status, gate_reason)
SELECT p.species_id, '8350f089-a800-430f-b698-a64fa98f399e', '541deded-ef79-4dc7-8016-7dac6a01486c', '10.1111/1365-2664.13120', 'Estimating national population sizes: methodological challenges and applications illustrated in the common nightingale, a declining songbird in the uk',
       'incident-audit', 'MISMATCH', 'rejected', 'common nightingale population methods — not gyrfalcon'
  FROM arctic.conservation_profiles p WHERE p.id = '8350f089-a800-430f-b698-a64fa98f399e'
ON CONFLICT DO NOTHING;

-- expected: 7 tombstoned rejected candidates restored
-- Assert before commit:
DO $$ BEGIN IF (SELECT count(*) FROM arctic.reference_candidates WHERE binding_status='rejected') < 7
  THEN RAISE EXCEPTION 'tombstone restore incomplete'; END IF; END $$;
COMMIT;
