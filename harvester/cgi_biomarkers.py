import re
import pandas
import json
import copy

""" https://www.cancergenomeinterpreter.org/biomarkers """

def _get_biomarker_type(alteration_type, biomarker):
    """ Map alteration type to standardized biomarker type. """

    # Dictionary to look up simple types.
    ALTERATION_TYPE_TO_BIOMARKER_TYPE = {
        "BIA":  "biallelic inactivation",
        "EXPR": "overexpression",
        "FUS": "fusion",
        "MUT": "snp"
    }

    rval = ''
    if alteration_type in ALTERATION_TYPE_TO_BIOMARKER_TYPE:
        rval = ALTERATION_TYPE_TO_BIOMARKER_TYPE[alteration_type]
    elif alteration_type == "CNA":
        # Copy number alteration, either amplification or deletion.
        if "amplification" in biomarker:
            rval = "amplification"
        elif "deletion" in biomarker:
            rval = "deletion"

    return rval


def _get_evidence(gene_ids, path='./cgi_biomarkers_per_variant.tsv'):
    """ load tsv """
    df = pandas.read_table(path)
    # change nan to blank string
    df = df.fillna('')
    # if no gene list return all
    if not gene_ids:
        dict_list = df.to_dict(orient='records')
    else:
        rows = df.loc[df['Gene'].isin(gene_ids)]
        dict_list = rows.to_dict(orient='records')
    for row in dict_list:
        yield row


def convert(evidence):
    """
    ['Primary Tumor type', 'Drug family', 'Alteration type', 'Targeting',
    'Assay type', 'Evidence level', 'Biomarker', 'Drug', 'Alteration',
    'Source', 'Curator', 'Comments', 'Drug status', 'Drug full name',
    'TCGI included', 'Curation date', 'Gene', 'Metastatic Tumor Type',
    'Association']
    {'Primary Tumor type': 'GIST', 'Drug family': '[HSP90 inhibitor]',
     'Alteration type': 'MUT', 'Targeting': nan, 'Assay type': nan,
     'Evidence level': 'Pre-clinical',
     'Biomarker': 'KIT mutation in exon 9 or 17',
     'Drug': '[]',
     'Alteration': 'KIT:788-828,449-514',
     'Source': 'PMID:21737509', 'Curator': 'RDientsmann',
     'Comments': nan, 'Drug status': nan,
     'Drug full name': 'HSP90 inhibitors',
     'TCGI included': True, 'Curation date': '01/16',
     'Gene': 'KIT', 'Metastatic Tumor Type': nan,
     'Association': 'Responsive'}
    """

    def split_gDNA(gDNA):
        ''' Split gDNA field of the form 'chr9:g.133747588G>C' and return dictionary. '''

        # TODO: handle non-SNPs like chr1:g.43815009_43815010delGGinsTT
        try:
            chrom, remainder = gDNA.split(':g.')
            if chrom.startswith('chr'):
                chrom = chrom[3:]
            start = re.search(r'(\d+)', remainder).group()
            ref, alt = remainder[len(start):].split(">")
            return {
                'chromosome': chrom,
                'start': start,
                'ref': ref,
                'alt': alt
            }
        except Exception as e:
            return {}

    # Create document for insertion.
    gene = evidence['Gene']
    feature = split_gDNA(evidence['gDNA'])

    feature['biomarker_type'] = _get_biomarker_type(evidence['Alteration type'], evidence['Biomarker'])
    feature['geneSymbol'] = gene
    feature['name'] = evidence['Biomarker']
    feature['description'] = evidence['Alteration']

    association = {}
    association['description'] = '{} {} {}'.format(gene,
                                                   evidence['Drug full name'],
                                                   evidence['Association'])
    association['environmentalContexts'] = []
    association['environmentalContexts'].append({
        'description': evidence['Drug full name']})
    phenotype_description = evidence['Primary Tumor type']
    if not evidence['Metastatic Tumor Type'] == '':
        phenotype_description = '{} {}'.format(
                phenotype_description, evidence['Metastatic Tumor Type'])
    association['phenotype'] = {
        'description': phenotype_description
    }

    pubs = []
    for p in evidence['Source'].split(';'):
        t = None
        if ':' in p:
            t, id = p.split(':')
        if t == 'PMID':
            pubs.append('http://www.ncbi.nlm.nih.gov/pubmed/{}'.format(id))
        else:
            pubs.append('https://www.google.com/#q={}'.format(p))

    association['evidence'] = [{
        "evidenceType": {
            "sourceName": "cgi"
        },
        'description': evidence['Association'],
        'info': {
            'publications': pubs
        }
    }]
    # add summary fields for Display
    association['evidence_label'] = '{} {}'.format(evidence['Association'],
                                                   evidence['Evidence level'])
    association['publication_url'] = pubs[0]
    association['drug_labels'] = evidence['Drug full name']
    feature_association = {'gene': gene,
                           'feature': feature,
                           'association': association,
                           'source': 'cgi',
                           'cgi': evidence}

    yield feature_association


def harvest(genes=None, drugs=None):
    """ get data from cgi """
    for evidence in _get_evidence(genes):
        yield evidence


def harvest_and_convert(genes=None, drugs=None):
    """ get data from cgi, convert it to ga4gh and return via yield """
    for evidence in harvest(genes, drugs):
        # print "harvester_yield {}".format(evidence.keys())
        # print evidence
        for feature_association in convert(evidence):
            # print "cgi convert_yield {}".format(feature_association.keys())
            yield feature_association


def _test():
    for feature_association in harvest_and_convert(['KIT']):
        print feature_association.keys()

if __name__ == '__main__':
    _test()
