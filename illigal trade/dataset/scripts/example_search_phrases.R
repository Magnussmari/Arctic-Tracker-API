# A script to generate search phrases of wildlife species seized in the illegal
# wildlife trade. Three examples include: (i) get all common names of seized 
# wildlife from the GBIF database, (ii) get taxa and use-type combinations with
# the species and common names associated with them, and (iii) a more specific
# example of the species and common names of all bird species recorded as being
# seized as feathers.


# ---------------------------------------------------------------------------- #

# load in libraries

library(dplyr)
library(readr)
library(stringr)

# ---------------------------------------------------------------------------- #

# load in data

## use-taxa combinations
use_taxa = read_csv('data/01_taxa_use_combos.csv', col_types = cols(.default = "c"))

## gbif taxonomic key
gbif_key = read_csv('data/02_gbif_taxonomic_key.csv', col_types = cols(.default = "c"))

## gbif common names
gbif_common_names = readRDS('data/03_gbif_common_names.rds')
# gbif_common_names = read_csv('data/03_gbif_common_names.csv', col_types = cols(.default = "c"))

## database common/generic names
db_common_names = read_csv('data/04_db_generic_common_names.csv', col_types = cols(.default = "c"))

## search words for use-types
use_search_words = read_csv('data/05_use_search_words.csv', col_types = cols(.default = "c"), na = "NA")


# ---------------------------------------------------------------------------- #

# 1. GBIF common names for each taxonomic rank

## all species common names
species_cns = 
  gbif_key %>% 
  distinct(id_species) %>% 
  left_join(gbif_common_names %>% 
              filter(`English name of Language` == "English"), 
            by = c("id_species" = "gbif_id")) %>% 
  distinct(gbif_common_name) %>% 
  filter(!is.na(gbif_common_name)) %>% 
  pull()


## all genera common names
genera_cns = 
  gbif_key %>% 
  distinct(id_genus) %>% 
  left_join(gbif_common_names %>% 
              filter(`English name of Language` == "English"), 
            by = c("id_genus" = "gbif_id")) %>% 
  distinct(gbif_common_name) %>% 
  filter(!is.na(gbif_common_name)) %>% 
  pull()


## all family common names
family_cns = 
  gbif_key %>% 
  distinct(id_family) %>% 
  left_join(gbif_common_names %>% 
              filter(`English name of Language` == "English"), 
            by = c("id_family" = "gbif_id")) %>% 
  distinct(gbif_common_name) %>% 
  filter(!is.na(gbif_common_name)) %>% 
  pull()

## all order common names
order_cns = 
  gbif_key %>% 
  distinct(id_order) %>% 
  left_join(gbif_common_names %>% 
              filter(`English name of Language` == "English"), 
            by = c("id_order" = "gbif_id")) %>% 
  distinct(gbif_common_name) %>% 
  filter(!is.na(gbif_common_name)) %>% 
  pull()

## all class common names
class_cns = 
  gbif_key %>% 
  distinct(id_class) %>% 
  left_join(gbif_common_names %>% 
              filter(`English name of Language` == "English"), 
            by = c("id_class" = "gbif_id")) %>% 
  distinct(gbif_common_name) %>% 
  filter(!is.na(gbif_common_name)) %>% 
  pull()


## all phylum common names
phylum_cns = 
  gbif_key %>% 
  distinct(id_phylum) %>% 
  left_join(gbif_common_names %>% 
              filter(`English name of Language` == "English"), 
            by = c("id_phylum" = "gbif_id")) %>% 
  distinct(gbif_common_name) %>% 
  filter(!is.na(gbif_common_name)) %>% 
  pull()

## all kingdom common names
kingdom_cns = 
  gbif_key %>% 
  distinct(id_kingdom) %>% 
  left_join(gbif_common_names %>% 
              filter(`English name of Language` == "English"), 
            by = c("id_kingdom" = "gbif_id")) %>% 
  distinct(gbif_common_name) %>% 
  filter(!is.na(gbif_common_name)) %>% 
  pull()

## combine into one vector and get unique
gbif_cns = unique( c(species_cns, genera_cns, family_cns,
                     order_cns, class_cns, phylum_cns, kingdom_cns))


# ---------------------------------------------------------------------------- #

# 2. use-taxa combinations

## with scientific name
use_taxa_sciname = 
  use_taxa %>% 
  left_join(gbif_key, by = c("db", "gbif_id", "db_taxa_name")) %>% 
  left_join(use_search_words, by = "standardized_use_id") %>% 
  select(gbif_name, search_word) %>% 
  filter(!is.na(gbif_name)) %>% 
  distinct() %>% 
  mutate(search_phrase = paste(gbif_name, search_word) %>% str_trim()) %>% 
  pull(search_phrase)

## with GBIF common name
use_taxa_gbif_cns = 
  use_taxa %>% 
  left_join(gbif_common_names %>% 
              filter(`English name of Language` == "English"), 
            by = "gbif_id") %>% 
  left_join(use_search_words, by = "standardized_use_id") %>% 
  select(gbif_common_name, search_word) %>% 
  filter(!is.na(gbif_common_name)) %>% 
  distinct() %>% 
  mutate(search_phrase = paste(gbif_common_name, search_word) %>% str_trim()) %>% 
  pull(search_phrase)

## with database common and generic names
use_taxa_db_cns = 
  use_taxa %>% 
  left_join(db_common_names, by = c("db", "db_taxa_name")) %>% 
  left_join(use_search_words, by = "standardized_use_id") %>% 
  select(db_name, search_word) %>% 
  filter(!is.na(db_name)) %>% 
  distinct() %>% 
  mutate(search_phrase = paste(db_name, search_word) %>% str_trim()) %>% 
  pull(search_phrase)

## combine to one vector and get unique
use_taxa_phrases = unique(c(use_taxa_sciname, use_taxa_gbif_cns, 
                            use_taxa_db_cns))


# ---------------------------------------------------------------------------- #


# A more specific search: the common names of all bird species seized as feathers

## first get GBIF common names
bird_spp_feather_gbif_cns = 
  use_taxa %>% 
  filter(standardized_use_type == "feather") %>% 
  left_join(gbif_key, by = c("db", "gbif_id", "db_taxa_name")) %>% 
  filter(gbif_rank %in% c("species", "subspecies")) %>% 
  filter(class == "Aves") %>%
  left_join(gbif_common_names %>% 
              filter(`English name of Language` == "English"), 
            by = "gbif_id") %>% 
  distinct(gbif_common_name) %>% 
  filter(!is.na(gbif_common_name)) %>% 
  pull(gbif_common_name)

## second get database common names
bird_spp_feather_db_cns = 
  use_taxa %>% 
  filter(standardized_use_type == "feather") %>% 
  left_join(gbif_key, by = c("db", "gbif_id", "db_taxa_name")) %>% 
  filter(gbif_rank %in% c("species", "subspecies")) %>% 
  filter(class == "Aves") %>%
  left_join(db_common_names, by = c("db", "db_taxa_name")) %>% 
  distinct(db_name) %>% 
  filter(!is.na(db_name)) %>% 
  pull(db_name)

## combine them and get unique
bird_spp_feather = unique(c(bird_spp_feather_gbif_cns, bird_spp_feather_db_cns))

## can add 'feather' to each name if desired
bird_spp_feather2 = paste(bird_spp_feather, "feather")
