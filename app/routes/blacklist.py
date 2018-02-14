# a set of blacklisted terms that reactapp user can't select from
blacklist = {"http://purl.org/dc/elements/1.1/identifier", "http://biohackathon.org/resource/faldo#Begin",
             "http://biohackathon.org/resource/faldo#ExactPosition", "https://www.github.com/superphy#isFoundIn",
             "http://biohackathon.org/resource/faldo#Reference", "http://biohackathon.org/resource/faldo#End",
             "http://www.w3.org/1999/02/22-rdf-syntax-ns#List", "http://biohackathon.org/resource/faldo#Region",
             "http://www.w3.org/2000/01/rdf-schema#domain", "https://www.github.com/superphy#hasPart",
             "http://biohackathon.org/resource/faldo#ReverseStrandPosition",
             "http://purl.org/dc/elements/1.1/description", "http://www.w3.org/2000/01/rdf-schema#Class",
             "http://www.w3.org/2000/01/rdf-schema#subPropertyOf", "http://www.w3.org/2000/01/rdf-schema#Datatype",
             "http://www.w3.org/2002/07/owl#ObjectProperty", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
             "http://www.biointerchange.org/gfvo#Description", "http://www.w3.org/2002/07/owl#TransitiveProperty",
             "http://www.w3.org/2000/01/rdf-schema#subClassOf", "http://purl.obolibrary.org/obo/SO_0001462",
             "http://www.biointerchange.org/gfvo#Contig", "http://www.w3.org/2000/01/rdf-schema#Resource",
             "http://www.biointerchange.org/gfvo#Genome", "http://www.w3.org/2000/01/rdf-schema#range",
             "http://purl.org/dc/elements/1.1/date", "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property"}

# a mapping of the readable form of a uri to their actual uri in blazegraph
# readable = bidict({
#     "http://purl.obolibrary.org/obo/GENEPIO_0001076":"O-Type",
#     "http://purl.obolibrary.org/obo/GENEPIO_0001077":"H-Type",
#     "https://www.github.com/superphy#AntimicrobialResistanceGene":"AntimicrobialResistanceGene",
#     "http://www.biointerchange.org/gfvo#Identifier":"Accession",
#     "https://www.github.com/superphy#Marker":"Gene",
#     "https://www.github.com/superphy#spfyId":"spfyId",
#     "http://biohackathon.org/resource/faldo#Position":"Position",
#     "http://www.biointerchange.org/gfvo#DNASequence":"DNASequence",
#     "https://www.github.com/superphy#VirulenceFactor":"VirulenceFactor"
# })
