# iucn_scope_codes.csv — why this file exists

`arctic_api.species_iucn` carries both `scope_code` and `scope_description`, and
the description is lossy: twenty regional assessments carry code `2` (the Europe
region) and one carries code `EU` (the twenty-seven member states), and all
twenty-one are described as "Europe". A page that labels from the description
names a geography the assessment was not made at — a category shown at a scope
it was not assessed at, which is the one claim this project refuses everywhere
else.

Measured 6 October 2026: the identifier table deposited that day gained species
names and **lost the scope code**, because it is written from
`Source Data/figure5_source_data.csv`, which carries only the description. That
was a trade dressed as an upgrade, and the app's `iucn-scope` test caught it.

So the codes are kept here, joined on `assessment_id`, taken from the identifier
table as it stood at ba45d2c where they were correct. They are IUCN's own
metadata, not Red List Data, and nothing here is withheld.

A blank `scope_code` is global, which is how the view holds it. The writer
refuses rather than guesses: an assessment with no code here, or a code that
disagrees with the row's own `scope`, stops the build.
