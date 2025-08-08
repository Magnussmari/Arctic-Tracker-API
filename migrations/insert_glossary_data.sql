-- Insert Glossary Data for Arctic Tracker
-- This script populates the glossary_terms table with all terms from the glossary document

-- Conservation Organizations & Frameworks
INSERT INTO glossary_terms (term, acronym, definition, category, priority, display_contexts) VALUES
('CITES', 'CITES', 'Convention on International Trade in Endangered Species of Wild Fauna and Flora. The primary international agreement ensuring that trade in wild animals and plants does not threaten their survival.', 'Conservation', 10, ARRAY['species_card', 'trade_tab', 'filters']),
('IUCN', 'IUCN', 'International Union for Conservation of Nature. Global authority on the status of the natural world and measures needed to safeguard it, publisher of the Red List.', 'Conservation', 10, ARRAY['species_card', 'conservation_tab']),
('NAMMCO', 'NAMMCO', 'North Atlantic Marine Mammal Commission. Regional body for cooperation on conservation, management and study of marine mammals in the North Atlantic.', 'Conservation', 8, ARRAY['species_card', 'catch_data']),
('iNaturalist', NULL, 'Global biodiversity observation network and social platform where naturalists, scientists, and the public share observations of biodiversity.', 'Conservation', 6, ARRAY['species_card']),
('CoP', 'CoP', 'Conference of the Parties. The decision-making body of CITES that meets every 2-3 years to review implementation and make decisions on species listings.', 'Conservation', 7, ARRAY['timeline', 'conservation_tab']);

-- IUCN Red List Categories
INSERT INTO glossary_terms (term, acronym, definition, category, subcategory, priority, display_contexts) VALUES
('Least Concern', 'LC', 'Species evaluated by IUCN with low risk of extinction. Widespread and abundant taxa are included in this category.', 'Conservation', 'IUCN Status', 9, ARRAY['species_card', 'filters']),
('Near Threatened', 'NT', 'Species close to qualifying for or likely to qualify for a threatened category in the near future.', 'Conservation', 'IUCN Status', 9, ARRAY['species_card', 'filters']),
('Vulnerable', 'VU', 'Species facing high risk of extinction in the wild in the medium-term future.', 'Conservation', 'IUCN Status', 9, ARRAY['species_card', 'filters']),
('Endangered', 'EN', 'Species facing very high risk of extinction in the wild in the near future.', 'Conservation', 'IUCN Status', 10, ARRAY['species_card', 'filters']),
('Critically Endangered', 'CR', 'Species facing extremely high risk of extinction in the wild in the immediate future.', 'Conservation', 'IUCN Status', 10, ARRAY['species_card', 'filters']),
('Extinct in the Wild', 'EW', 'Species known only to survive in cultivation, captivity, or as a naturalized population outside its historic range.', 'Conservation', 'IUCN Status', 8, ARRAY['species_card', 'filters']),
('Extinct', 'EX', 'Species for which there is no reasonable doubt that the last individual has died.', 'Conservation', 'IUCN Status', 8, ARRAY['species_card', 'filters']);

-- CITES Appendices
INSERT INTO glossary_terms (term, acronym, definition, category, subcategory, priority, display_contexts, related_terms) VALUES
('Appendix I', NULL, 'CITES listing for species threatened with extinction. Trade is permitted only in exceptional circumstances and requires both import and export permits.', 'Conservation', 'CITES', 10, ARRAY['species_card', 'trade_tab', 'filters'], ARRAY['CITES', 'Appendix II', 'Appendix III']),
('Appendix II', NULL, 'CITES listing for species not necessarily threatened with extinction, but trade must be controlled to avoid utilization incompatible with their survival.', 'Conservation', 'CITES', 10, ARRAY['species_card', 'trade_tab', 'filters'], ARRAY['CITES', 'Appendix I', 'Appendix III']),
('Appendix III', NULL, 'CITES listing for species protected in at least one country that has asked other CITES Parties for assistance in controlling trade.', 'Conservation', 'CITES', 8, ARRAY['species_card', 'trade_tab', 'filters'], ARRAY['CITES', 'Appendix I', 'Appendix II']);

-- Trade Terms - Specimen Types
INSERT INTO glossary_terms (term, definition, category, subcategory, priority, display_contexts) VALUES
('Specimens', 'Whole animals, dead or alive, in the context of wildlife trade.', 'Trade', 'Specimen Types', 7, ARRAY['trade_tab']),
('Skins', 'Whole, raw or tanned animal skins used in trade, including furs and pelts.', 'Trade', 'Specimen Types', 8, ARRAY['trade_tab']),
('Skin pieces', 'Parts of skins including scraps, often used in leather or fur products.', 'Trade', 'Specimen Types', 6, ARRAY['trade_tab']),
('Teeth', 'Animal teeth traded for various purposes, including tusks and ivory from marine mammals.', 'Trade', 'Specimen Types', 7, ARRAY['trade_tab']),
('Hair', 'Animal hair including wool and fur, traded for textile and other uses.', 'Trade', 'Specimen Types', 5, ARRAY['trade_tab']),
('Bones', 'Animal bones including skulls, traded for various purposes including traditional medicine and crafts.', 'Trade', 'Specimen Types', 6, ARRAY['trade_tab']),
('Meat', 'All meat parts and products from wildlife, traded for consumption.', 'Trade', 'Specimen Types', 7, ARRAY['trade_tab']),
('Live', 'Living specimens traded for zoos, aquariums, research, or private collections.', 'Trade', 'Specimen Types', 9, ARRAY['trade_tab']),
('Trophies', 'Hunting trophies including mounted specimens or parts kept as souvenirs.', 'Trade', 'Specimen Types', 7, ARRAY['trade_tab']),
('Scientific specimens', 'Specimens preserved specifically for scientific research and education.', 'Trade', 'Specimen Types', 6, ARRAY['trade_tab']);

-- Trade Purposes
INSERT INTO glossary_terms (term, acronym, definition, category, subcategory, priority, display_contexts) VALUES
('Breeding in captivity', 'B', 'Trade purpose code for specimens used in breeding programs or artificial propagation.', 'Trade', 'Purpose Codes', 5, ARRAY['trade_tab']),
('Educational', 'E', 'Trade purpose code for specimens used in educational programs and displays.', 'Trade', 'Purpose Codes', 5, ARRAY['trade_tab']),
('Botanical garden', 'G', 'Trade purpose code for plant specimens destined for botanical gardens.', 'Trade', 'Purpose Codes', 3, ARRAY['trade_tab']),
('Hunting trophy', 'H', 'Trade purpose code for specimens taken as hunting trophies.', 'Trade', 'Purpose Codes', 6, ARRAY['trade_tab']),
('Law enforcement', 'L', 'Trade purpose code for specimens used in law enforcement, judicial, or forensic purposes.', 'Trade', 'Purpose Codes', 4, ARRAY['trade_tab']),
('Medical', 'M', 'Trade purpose code for specimens used in medical or biomedical research.', 'Trade', 'Purpose Codes', 5, ARRAY['trade_tab']),
('Reintroduction', 'N', 'Trade purpose code for specimens being reintroduced or introduced into the wild.', 'Trade', 'Purpose Codes', 5, ARRAY['trade_tab']),
('Personal', 'P', 'Trade purpose code for personal use, typically tourist souvenirs.', 'Trade', 'Purpose Codes', 6, ARRAY['trade_tab']),
('Circus/Exhibition', 'Q', 'Trade purpose code for specimens used in circuses or traveling exhibitions.', 'Trade', 'Purpose Codes', 4, ARRAY['trade_tab']),
('Scientific', 'S', 'Trade purpose code for specimens used in scientific research.', 'Trade', 'Purpose Codes', 7, ARRAY['trade_tab']),
('Commercial', 'T', 'Trade purpose code for commercial trade in specimens.', 'Trade', 'Purpose Codes', 8, ARRAY['trade_tab']),
('Zoo', 'Z', 'Trade purpose code for specimens destined for zoos.', 'Trade', 'Purpose Codes', 6, ARRAY['trade_tab']);

-- Source Codes
INSERT INTO glossary_terms (term, acronym, definition, category, subcategory, priority, display_contexts) VALUES
('Wild', 'W', 'Source code for specimens taken from the wild.', 'Trade', 'Source Codes', 9, ARRAY['trade_tab']),
('Ranched', 'R', 'Source code for specimens from ranching operations.', 'Trade', 'Source Codes', 5, ARRAY['trade_tab']),
('Captive-bred (commercial)', 'D', 'Source code for Appendix-I animals bred in captivity for commercial purposes.', 'Trade', 'Source Codes', 5, ARRAY['trade_tab']),
('Artificially propagated', 'A', 'Source code for plants artificially propagated for commercial purposes.', 'Trade', 'Source Codes', 3, ARRAY['trade_tab']),
('Captive-bred', 'C', 'Source code for animals bred in captivity (Appendix II/III).', 'Trade', 'Source Codes', 6, ARRAY['trade_tab']),
('Captive-born', 'F', 'Source code for animals born in captivity (F1 or subsequent generations).', 'Trade', 'Source Codes', 5, ARRAY['trade_tab']),
('Confiscated', 'I', 'Source code for confiscated or seized specimens.', 'Trade', 'Source Codes', 4, ARRAY['trade_tab']),
('Pre-Convention', 'O', 'Source code for specimens acquired before CITES provisions applied.', 'Trade', 'Source Codes', 4, ARRAY['trade_tab']),
('Unknown source', 'U', 'Source code used when the source of specimens is unknown.', 'Trade', 'Source Codes', 5, ARRAY['trade_tab']),
('Marine environment', 'X', 'Source code for specimens taken in marine areas not under any jurisdiction.', 'Trade', 'Source Codes', 6, ARRAY['trade_tab']);

-- Taxonomic Terms
INSERT INTO glossary_terms (term, definition, category, priority, display_contexts, related_terms) VALUES
('Kingdom', 'Highest taxonomic rank in biological classification (e.g., Animalia for animals, Plantae for plants).', 'Taxonomy', 7, ARRAY['species_detail'], ARRAY['Phylum', 'Class', 'Order', 'Family', 'Genus', 'Species']),
('Phylum', 'Major lineage within a kingdom in biological classification (e.g., Chordata for vertebrates).', 'Taxonomy', 7, ARRAY['species_detail'], ARRAY['Kingdom', 'Class']),
('Class', 'Taxonomic rank below phylum and above order (e.g., Mammalia for mammals, Aves for birds).', 'Taxonomy', 8, ARRAY['species_card', 'filters'], ARRAY['Order', 'Family']),
('Order', 'Taxonomic rank below class and above family (e.g., Carnivora for carnivorous mammals, Cetacea for whales and dolphins).', 'Taxonomy', 7, ARRAY['species_detail', 'filters'], ARRAY['Class', 'Family']),
('Family', 'Taxonomic rank below order and above genus (e.g., Ursidae for bears, Delphinidae for dolphins).', 'Taxonomy', 8, ARRAY['species_card', 'filters'], ARRAY['Order', 'Genus']),
('Genus', 'Taxonomic rank below family and above species. First part of the scientific name (e.g., Ursus for bears).', 'Taxonomy', 7, ARRAY['species_detail'], ARRAY['Family', 'Species', 'Scientific name']),
('Species', 'Basic unit of biological classification. The full scientific name consists of genus + species (e.g., Ursus maritimus).', 'Taxonomy', 9, ARRAY['species_card', 'species_detail'], ARRAY['Genus', 'Scientific name']),
('Scientific name', 'Binomial nomenclature using Latin to uniquely identify species (Genus species format).', 'Taxonomy', 10, ARRAY['species_card', 'search'], ARRAY['Genus', 'Species', 'Common name']),
('Common name', 'Vernacular or colloquial name for a species in local language (e.g., Polar Bear for Ursus maritimus).', 'Taxonomy', 9, ARRAY['species_card', 'search'], ARRAY['Scientific name']);

-- Data & Analysis Terms
INSERT INTO glossary_terms (term, definition, category, priority, display_contexts) VALUES
('Trade volume', 'Total quantity of specimens involved in international trade over a specific period.', 'Data', 6, ARRAY['trade_tab', 'charts']),
('Trade records', 'Individual documented transactions of wildlife trade, including species, quantity, countries, and purpose.', 'Data', 7, ARRAY['trade_tab']),
('Reported quantity', 'The amount of specimens declared in official trade documentation, which may differ between importers and exporters.', 'Data', 5, ARRAY['trade_tab']),
('Importer/Exporter', 'Countries involved in wildlife trade. Importers receive specimens; exporters send them.', 'Data', 7, ARRAY['trade_tab', 'charts']),
('Timeline events', 'Significant conservation milestones such as CITES listings, IUCN assessments, or major policy changes.', 'Data', 6, ARRAY['timeline']),
('Population trend', 'Direction of population change over time: increasing, stable, decreasing, or unknown.', 'Data', 8, ARRAY['species_card', 'conservation_tab']),
('Conservation assessment', 'Formal evaluation of a species'' conservation status, typically by IUCN Red List criteria.', 'Data', 7, ARRAY['conservation_tab']),
('Catch data', 'Harvest or hunting records, particularly from NAMMCO for marine mammals in the North Atlantic.', 'Data', 7, ARRAY['catch_tab', 'charts']);

-- Geographic & Administrative Terms
INSERT INTO glossary_terms (term, definition, category, priority, display_contexts, related_terms) VALUES
('Range states', 'Countries where a species naturally occurs within its native distribution.', 'Geography', 7, ARRAY['species_detail', 'conservation_tab'], ARRAY['Arctic region']),
('Party/Parties', 'Countries that have formally joined CITES and are bound by its provisions. Currently 184 Parties.', 'Geography', 6, ARRAY['trade_tab'], ARRAY['Non-Party', 'CITES']),
('Non-Party', 'Country that has not joined CITES. Trade with non-Parties requires comparable documentation.', 'Geography', 5, ARRAY['trade_tab'], ARRAY['Party/Parties', 'CITES']),
('Split-listing', 'When different populations of the same species have different CITES appendix listings based on geographic location.', 'Geography', 6, ARRAY['species_detail', 'conservation_tab'], ARRAY['CITES', 'Appendix I', 'Appendix II']),
('Arctic region', 'Circumpolar north including the Arctic Ocean and northern parts of Canada, Russia, USA (Alaska), Greenland, Norway, Sweden, Finland, and Iceland. Definition varies by context.', 'Geography', 9, ARRAY['filters', 'about'], ARRAY['Range states']);

-- Add CMS terms (new addition based on recent integration)
INSERT INTO glossary_terms (term, acronym, definition, category, priority, display_contexts, related_terms) VALUES
('CMS', 'CMS', 'Convention on the Conservation of Migratory Species of Wild Animals (Bonn Convention). International treaty protecting migratory species across their range.', 'Conservation', 9, ARRAY['species_card', 'conservation_tab'], ARRAY['CITES', 'IUCN']),
('CMS Appendix I', NULL, 'Endangered migratory species requiring strict protection across their range. Parties must protect habitats and prohibit taking.', 'Conservation', 8, ARRAY['species_card', 'conservation_tab'], ARRAY['CMS', 'CMS Appendix II']),
('CMS Appendix II', NULL, 'Migratory species that would benefit from international cooperation for conservation and management.', 'Conservation', 8, ARRAY['species_card', 'conservation_tab'], ARRAY['CMS', 'CMS Appendix I']);