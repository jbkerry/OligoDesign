#!/usr/bin/env python

import re
import sys
import pickle

import numpy as np

from Bio import SeqIO

rs_dict = {'DpnII': 'GATC',
           'NlaIII': 'CATG',
           'HindIII': 'AAGCTT'}

def gen_oligos(fa, bed, enzyme='DpnII', oligo=70):
    '''Generates oligos flanking restriction fragments that encompass the\n
    coordinates supplied in the bed file\n\n
    
    Parameters\n
    \----------\n
    fa: path to reference genome fasta\n
    bed: tab-delimited bed file containing a list of coordinates for viewpoints\n
        in the capture experiment.\n
        Must be in the format 'chr'\t'start'\t'stop'\t'name'\n
    enzyme: DpnII (GATC), NlaIII (CATG) or HindIII (AAGCTT), default=DpnII\n
    oligo: the length of the oligo to design (bp), default=70\n\n
    
    Returns\n
    \-------\n
    oligo_seqs: dictionary containing oligo coordinates as keys and oligo\n
        sequences as items\n\n
    associations: dictionary containing the fragment coordinates as keys and
        the associated gene names as a comma-separated string
    not_done: dictionary containing viewpoint coordinates of all those sites
        that oligos were not generated for. The corresponding value is a tuple
        with the gene name at index 0 and the reason at index 1
    
    '''
    
    cut_sites = {}
    oligo_seqs = {}
    associations = {}
    cut_size = len(rs_dict[enzyme])
    p = re.compile(rs_dict[enzyme])
    
    print('Loading reference fasta file...')
    seq_dict = SeqIO.to_dict(SeqIO.parse(fa, 'fasta'))
    for x in seq_dict:
        seq = str(seq_dict[x].seq).upper()
        cut_sites[x] = [m.start() for m in p.finditer(seq)]
        cut_sites[x] = np.array(cut_sites[x])
    print('\t...complete\nGenerating oligos...')
    
    with open(bed) as w:
        for x in w:
            chr_name, start, stop, name = x.strip().split('\t')
            
            if '_' in chr_name: continue
            
            vp_coor = '{}:{}-{}'.format(chr_name, start, stop)
            start, stop = map(int, (start, stop))
            seq = seq_dict[chr_name].seq.upper()
            
            l_start = cut_sites[chr_name][cut_sites[chr_name]<=start][-1]
            r_stop = cut_sites[chr_name][cut_sites[chr_name]>=start][0] + cut_size # currently this picks an adjacent fragment if the site is in a cutsite; are we okay with that?
            frag_len = r_stop - l_start
            
            if frag_len>=oligo:
                l_stop = l_start + oligo
                r_start = r_stop - oligo
                
                l_tup = (l_start, l_stop, l_start, r_stop)
                r_tup = (r_start, r_stop, l_start, r_stop)
                l_seq = seq[l_start:l_stop]
                r_seq = seq[r_start:r_stop]
                
                frag_key = '{}:{}-{}'.format(chr_name, l_start, r_stop)
                associations[frag_key] = '{}{},'.format(
                    associations.get(frag_key, ''),
                    name)
                
                l_key = '{}:{}-L'.format(chr_name, '-'.join(map(str, l_tup)))
                if l_key in oligo_seqs:
                    print('{} ({}) is redundant to another position'.format(
                        vp_coor, name), file=sys.stderr)
                    #not_done[vp_coor] = (name, 0) # 0 = redundant
                    continue
                
                oligo_seqs[l_key] = str(l_seq)
                if frag_len>oligo:
                    oligo_seqs['{}:{}-R'.format(chr_name,
                                           '-'.join(map(str, r_tup)))
                            ] = str(r_seq)
            else:
                print('{} ({}) was in a fragment that was too small'.format(
                        vp_coor, name), file=sys.stderr)
    
    pickle.dump(associations, open('_tmp.p', 'wb'))
    print('\t...complete')
    return oligo_seqs

if __name__ == '__main__':
    
    import tools
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        '--fasta',
        type = str,
        help = 'Path to reference genome fasta.',
        required = True,
    )
    parser.add_argument(
        '-g',
        '--genome',
        type = str,
        help = 'Genome build e.g. \'mm10\' or \'hg38\'.',
        required = True,
    )
    parser.add_argument(
        '-b',
        '--bed',
        type = str,
        help = 'Path to bed file with capture viewpoint coordinates',
        required = True,
    )
    parser.add_argument(
        '-o',
        '--oligo',
        type = int,
        help = 'The size (in bp) of the oligo to design, default=70',
        default = 70,
        required = False,
    )
    parser.add_argument(
        '-e',
        '--enzyme',
        type = str,
        help = 'Name of restriction enzyme, default=DpnII',
        default = 'DpnII',
        required = False,
    )
    parser.add_argument(
        '-s',
        '--star_index',
        type = str,
        help = 'Path to STAR index directory. Omit this option if running ' \
               'with BLAT (--blat)',
        required = False,
    )
    parser.add_argument(
        '--blat',
        action = 'store_true',
        help = 'Detect off-targets using BLAT instead of STAR.',
        required = False,
    )
    parser.add_argument(
        '--test_fasta',
        action = 'store_true',
        help = argparse.SUPPRESS,
        required = False,
    )
    
    args = parser.parse_args()
    
    if not args.blat and not args.star_index:
        msg = '-s/--star_index argument is required if --blat is not selected'
        parser.error(msg)
    
    pass_seqs = gen_oligos(
        fa = args.fasta,
        bed = args.bed,
        enzyme = args.enzyme,
        oligo = args.oligo,
    )
    tools.write_oligos(oligo_seqs=pass_seqs)
    if not args.test_fasta:
        tools.check_off_target(
            genome = args.genome,
            fa = args.fasta,
            s_idx = args.star_index,
            blat=args.blat,
        )
        tools.get_density(blat=args.blat)
