#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

# use: python -m scripts.savvy -i /home/kevin/Desktop/nonGenBankEcoli/ECI-2866_lcl.fasta

# S:erotype
# A:ntimicrobial Resistance
# V:irulence Factors
# -vy
# essentially implements the same pipeline as blob_savvy_enqueue() in spfy.py, but without the RQ backing
# still graphs the results, so must have blazegraph running and defined in app/config.py

import os
import logging
import tempfile
import shutil
import json
from modules.qc.qc import qc
from middleware.blazegraph.reserve_id import write_reserve_id
from modules.ectyper.call_ectyper import call_ectyper_vf, call_ectyper_serotype
from modules.amr.amr import amr
from modules.amr.amr_to_dict import amr_to_dict
from middleware.display.beautify import beautify
from middleware.graphers.datastruct_savvy import generate_datastruct
from middleware.graphers.turtle_grapher import generate_turtle_skeleton
from middleware.graphers.turtle_utils import generate_hash, generate_uri as gu
from modules.loggingFunctions import initialize_logging
from middleware.blazegraph.reserve_id import reservation_triple

log_file = initialize_logging()
log = logging.getLogger(__name__)


def get_spfyid_file():
    """
    Uses tempfile to store the spfyid file on disk.
    We use a mmethod so the tests can access just the file as well.
    """
    f = os.path.join(tempfile.gettempdir(), 'spfyid_count.txt')
    return f


def mock_reserve_id():
    """
    Mocks the presence of Blazegraph to generate spfyids.
    """
    f = get_spfyid_file()
    log.debug('spfyid_count file returned was : ' + f)
    # check if an existing spfyid count exists
    if os.path.isfile(f):
        with open(f) as fl:
            spfyid = fl.read()
            spfyid = int(spfyid)
    else:
        spfyid = 0
    # we assumed the spfyid in the file is already used
    spfyid += 1
    with open(f, 'w') as fl:
        fl.write(str(spfyid))
    return spfyid


def savvy(args_dict, return_graphs=False):
    """
    Mimicks the spfy pipeline without RQ backend or Blazegraph.
    Generate three turtle files:
        1. the graph of a base result for some fasta file
        2. the graph of the ectyper result
        3. the graph of the rgi result
    And two JSON files:
        1. the json result for ectyper after parsing by beautify
        2. the json result for rgi after parsing by beautify
    """

    def write_graph(graph, analysis):
        """
        Used to write a rdf graph to disk as a turtle file.
        """
        data = graph.serialize(format="turtle")
        f = query_file + '_' + analysis + '.ttl'
        with open(f, 'w') as fl:
            fl.write(data)
        return f

    def write_json(json_r, analysis):
        """
        Used to write out a .json result after processing by beautify.py
        Note that we use flask.jsonify in the backend application instead of
        the json.dump method used here.
        """
        f = query_file + '_' + analysis + '.json'
        with open(f, 'w') as fl:
            json.dump(json_r, fl)
        return f

    log.debug("Starting savvy.py from savvy(). Logfile is: " + str(log_file))
    log.debug("args_dict received was: " + str(args_dict))

    query_file = args_dict['i']
    log.debug("query_file is: " + query_file)

    # (1) QC Step:
    qc_pass = qc(query_file)
    assert qc(query_file) == True
    log.debug("QC: " + str(qc_pass))

    # (2) SpfyID Step:
    # we use mock to create a spfyid file, note that we dont need the
    # return as spfy methods will read from the file
    mock_reserve_id()
    # spfy expects id files and fasta files to be in the same location
    id_file = os.path.abspath(query_file) + '_id.txt'
    shutil.copy(get_spfyid_file(), id_file)
    log.debug("id_file:" + id_file)

    # Call PanPredic
    # panpredic_p = pan(args_dict)

    # (2b) Create the reservation_triple:
    graph = generate_turtle_skeleton(query_file)
    file_hash = generate_hash(query_file)
    uriGenome = gu(':' + file_hash)
    reservation_graph = reservation_triple(graph, uriGenome, 1)
    reservation_ttl = write_graph(reservation_graph, 'reservation')

    # (3) ECTyper Step:
    ectyper_p = call_ectyper_vf(args_dict)  # call_ectyper_vf is the older ver.
    log.debug("Pickled ECTyper File: " + ectyper_p)

    # (4) ECTyper Beautify Step:
    ectyper_beautify = beautify(args_dict, ectyper_p)
    log.debug('Beautified ECTyper Result: ' + str(ectyper_beautify))
    ectyper_json = write_json(ectyper_beautify, 'ectyper')

    # (5) Graphing ECTyper Result:
    ectyper_graph = generate_datastruct(query_file, query_file + '_id.txt', ectyper_p)

    ectyper_ttl = write_graph(ectyper_graph, 'ectyper')
    log.debug('Graph Result for ECtyper: ' + ectyper_ttl)

    # (6) RGI Step:
    amr_results_file = amr(query_file)
    log.debug("AMR Results File: " + amr_results_file)

    # (7) AMR Results to Dictionary Step:
    amr_p = amr_to_dict(amr_results_file)
    log.debug("Pickled AMR Results File: " + amr_p)

    # (8) AMR Beautify Step:
    amr_beautify = beautify(args_dict, amr_p)
    log.debug('Beautified AMR Result: ' + str(amr_beautify))
    amr_json = write_json(amr_beautify, 'rgi')

    # (9) Graping AMR Result:
    amr_graph = generate_datastruct(query_file, query_file + '_id.txt', query_file + '_rgi.tsv_rgi.p')
    amr_ttl = write_graph(amr_graph, 'rgi')
    log.debug('Graph Result for AMR: ' + amr_ttl)

    # (10) Base Graphing:
    base_turtle_graph = generate_turtle_skeleton(query_file)
    base_ttl = write_graph(base_turtle_graph, 'base')
    log.debug('Graph Result for base of fasta info: ' + base_ttl)
    if return_graphs:
        return base_turtle_graph, ectyper_graph, amr_graph
    else:
        return base_ttl, ectyper_ttl, amr_ttl, ectyper_json, amr_json


if __name__ == "__main__":
    import argparse

    log.debug("Starting savvy.py from if __name__=='__main__'. Logfile is: " + str(log_file))

    # parsing cli-input
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        help="FASTA file",
        required=True
    )
    parser.add_argument(
        "--disable-serotype",
        help="Disables use of the Serotyper. Serotyper is triggered by default.",
        action="store_true"
    )
    parser.add_argument(
        "--disable-vf",
        help="Disables use of ECTyper to get associated Virulence Factors. VFs are computed by default.",
        action="store_true"
    )
    parser.add_argument(
        "--disable-amr",
        help="Disables use of RGI to get Antimicrobial Resistance Factors.  AMR genes are computed by default.",
        action="store_true"
    )
    parser.add_argument("--pi",
                        type=int,
                        help="Percentage of identity wanted to use against the database. From 0 to 100, default is 90%.",
                        default=90, choices=range(0, 100))
    args = parser.parse_args()
    # we make a dictionary from the cli-inputs and add are uris to it
    # mainly used for when a func needs a lot of the args
    args_dict = vars(args)

    # check/convert file to abspath
    args_dict['i'] = os.path.abspath(args_dict['i'])

    # add nested dictionary to mimick output from spfy web-app
    spfy_options = {'vf': not args_dict['disable_vf'], 'amr': not args_dict['disable_amr'],
                    'serotype': not args_dict['disable_serotype']}
    # the 'options' field represents things the user (of the web-app) has chosen to display, we still run ALL analysis on their files so their choices are not added to module calls (& hence kept separate)
    args_dict['options'] = spfy_options

    print savvy(args_dict)
