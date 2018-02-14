def pair(relation, human_readable=None):
    """
    Creates a dictionary pair of a relation uri in string form and a human readable equivalent.
    Args:
        relation (str): This should be preformated so generate_uri works on it
        human_readable (str): a plain-text description of the uri
    Return:
        d (dictionary)
    """
    d = {
        'relation': relation,
        'human_readable': human_readable
    }
    return d


# In this mapping, outer dictionary key represents the column header in the csv.
# We use the same header as the human-readable description so users are
# familiar with what they're selecting on group comparisons.
# Note: we don't handle "serotype" here as it has to be split into O and H type.
mapping = {
    'primary_dbxref': pair('ge:0001800', 'primary_dbxref'),
    'secondary_sample_accession': pair(':secondary_sample_accession', 'secondary_sample_accession'),
    'study_accession': pair('obi:0001628', 'study_accession'),
    'secondary_study_accession': pair(':secondary_study_accession', 'secondary_study_accession'),
    'strain': pair(':0001429', 'strain'),
    'serotype': '',
    'O-Type': pair('ge:0001076', 'O-Type'),
    'H-Type': pair('ge:0001077', 'H-Type'),
    'stx1_subtype': pair('subt:stx1', 'stx1_subtype'),
    'stx2_subtype': pair('subt:stx2', 'stx2_subtype'),
    'syndrome': pair('ge:0001613', 'syndrome'),
    'isolation_host': pair('ge:0001567', 'isolation_host'),
    'isolation_source': pair('ge:0000025', 'isolation_source'),
    'isolation_date': pair('ge:0000020', 'isolation_date'),
    'isolation_location': pair('ge:0000117', 'isolation_location'),
    'contact': pair('ge:0001642', 'contact')
}
