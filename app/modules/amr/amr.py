import subprocess
import os
import shutil


def amr(query_file):
    """
    Wrapper for RGI. Note RGI has a bug, namely:
    rgi.py, line 816, in runBlast
        with open(working_directory+"/"+outputFile+".json", 'w') as f:
    What this means is that while absolute files for '-i' are fine, rgi can not handle absolute paths for '-o'. Output files must only be a basename (& are thus outputting in your current directory) otherwise the base rgi call will fail.
    Note: As shown in the above code, RGI will also ignore extensions specified in '-o'
    """
    # we use this to address the bug in RGI
    # also, if you don't specify a '-o' in RGI call, it will try to save the final output as Report.json in your working directory (which breaks our multiprocessing (through RQ) use of RGI.
    outputname = os.path.basename(query_file)

    # differs from ectyper as we dont care about the temp results, just the final .tsv
    # direct (the main) call
    subprocess.call(['rgi',
                     '-i', query_file,
                     '-o', outputname])

    # the rgi_json call in rgitool.py isn't needed for us
    # this generates the '.tsv' we want (named as a '.txt')
    subprocess.call(['rgi_jsontab',
                     '-i', outputname + '.json',
                     '-o', outputname])

    # rename and move the tsv to the original directory, if applicable
    amr_file = query_file + '_rgi.tsv'
    shutil.move(outputname + '.txt', amr_file)

    return amr_file


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        help="FASTA file",
        required=True
    )
    args = parser.parse_args()
    print amr(args.i)
