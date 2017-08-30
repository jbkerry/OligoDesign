#!/usr/bin/env python

from __future__ import print_function, division

import argparse
import math
import re
import sys

import numpy as np  # >=1.7
from Bio import SeqIO  # >=1.60

from .tools import Tools

def check_value(values, labels):
    for value, label in zip(values, labels):
        if (value<1) | isinstance(value, float):
            raise ValueError(
                '{} must be an integer greater than 0'.format(label))
            break
    else:
        return None
    
def get_sequence(seq, *coors):
    for coor in coors:
        yield str(seq[coor[0]:coor[1]])

def get_oligo_coor(chrom, oligo, start, stop):

    def create_key(chrom, oligo_coor, frag_coor, side):
        key = ':'.join((chrom, '-'.join(map(str, (oligo_coor + frag_coor)))))
        key = '-'.join(key, side)
        
        return key
    
    left_coor = (l_start, l_stop) = (start, start + oligo)
    right_coor = (r_start, r_stop) = (stop - oligo, stop)
    frag_coor = (l_start, r_stop)
    
    l_key = create_key(chrom, left_coor, frag_coor, 'L')
    r_key = create_key(chrom, right_coor, frag_coor, 'R')
    
    coor = {
        'left': {'coor': (l_start, l_stop), 'key': l_key},
        'right': {'coor': (r_start, r_stop), 'key': r_key},
    }
    
    return coor

class Capture(Tools):
    """Designs oligos for Capture-C"""
    
    __doc__ += Tools.__doc__
    
    def __init__(self):
        super(Capture, self).__init__()
        
    def gen_oligos(self, bed, enzyme='DpnII', oligo=70):
        r"""Generates oligos flanking restriction fragments that encompass the
        coordinates supplied in the bed file
        
        Parameters
        ----------
        bed : str
            Path to tab-delimited bed file containing a list of coordinates for
            viewpoints in the capture experiment. Must be in the format
            'chr'\\t'start'\\t'stop'\\t'name'\\n
        enzyme : {'DpnII', 'NlaIII', 'HindIII'}, optional
            The enzyme for digestion, default = DpnII
        oligo : int, optional
            The length of the oligo to design (bp), default = 70
        
        Returns
        -------
        self : object
        
        """
        
        check_value((oligo,), ('Oligo size',))
        
        cut_sites = {}
        cut_size = len(recognition_seq[enzyme])
        p = re.compile(recognition_seq[enzyme])
        
        print('Loading reference fasta file...')
        seq_dict = SeqIO.to_dict(SeqIO.parse(self.fa, 'fasta'))
        for chrom, attr in seq_dict.items():
            seq = str(attr.seq).upper()
            cut_sites[x] = [m.start() for m in p.finditer(seq)]
            cut_sites[x] = np.array(cut_sites[x])
        print('\t...complete\nGenerating oligos...')
        
        with open(bed) as w:
            for x in w:
                chrom, start, stop, name = x.strip().split('\t')
                
                if '_' in chrom: continue
                
                vp_coor = '{}:{}-{}'.format(chrom, start, stop)
                start, stop = map(int, (start, stop))
                
                frag_start = cut_sites[chrom][cut_sites[chrom] <= start][-1]
                frag_stop = cut_sites[chrom][cut_sites[chrom] >= start][0] + cut_size # currently this picks an adjacent fragment if the site is in a cutsite; are we okay with that?
                frag_length = frag_stop - frag_start
                
                coors = get_oligo_coor(chrom, oligo, frag_start, frag_stop)
                
                if frag_length < oligo:
                    print('{} ({}) is in a fragment that is too small. '
                          'Skipping.'.format(vp_coor, name), file=sys.stderr)
                    continue
                
                chrom_seq = seq_dict[chrom].seq.upper()
                oligo_seq = get_sequence(chrom_seq, *(coors['left']['coor'],
                                                      coors['right']['coor']))
                
                l_key = coors['left']['key']
                if l_key in self.oligo_seqs:
                    print('{} ({}) is redundant to another position'.format(
                        vp_coor, name), file=sys.stderr)
                    continue
                
                self.oligo_seqs[l_key] = next(oligo_seq)     
                if frag_len > oligo:
                    self.oligo_seqs[coors['right']['key']] = next(oligo_seq)
                
                frag_key = '{}:{}-{}'.format(chrom, frag_start, frag_stop)
                self._assoc[frag_key] = '{}{},'.format(
                    self._assoc.get(frag_key, ''), name)
        
        print('\t...complete.')
        if __name__ != '__main__':
            print('Oligos stored in the oligo_seqs attribute')
        
        return self
    
    def __str__(self):
        
        return 'Capture-C oligo design object for the {} genome'.format(
            self.genome)
    
class Tiled(Tools):
    """Designs oligos adjacent to each other or on adjacent fragments"""
    
    __doc__ += Tools.__doc__
    
    def gen_oligos_capture(self, chrom, region='', enzyme='DpnII', oligo=70):
        """Designs oligos for multiple adjacent restriction fragments
        across a specified region of a chromosome, or for the entire
        chromosome.
        
        Parameters
        ----------
        chrom : str
            Chromosome number/letter e.g. 7 or X
        region : str, optional
            The region of the chromosome to design oligos, e.g.
            10000-20000; omit this option to design oligos over the
            entire chromosome
        enzyme : {'DpnII', 'NlaIII', 'HindIII'}, optional
            The enzyme for digestion, default=DpnII
        oligo : int, optional
            The length of the oligos to design (bp), default=70
            
        Returns
        -------
        self : object
    
        """
        
        check_value((oligo,), ('Oligo size',))
        
        chr_name = 'chr'+str(chrom)
        
        print('Loading reference fasta file...')
        seq_dict = SeqIO.to_dict(SeqIO.parse(self.fa, 'fasta'))
        seq = seq_dict[chr_name].seq.upper()
        print('\t...complete\nGenerating oligos...')
            
        if not region:
            start = 0; stop = len(seq)
        else:
            start, stop = map(int, region.split('-'))
        
        p = re.compile(recognition_seq[enzyme])
        pos_list = []
        for m in p.finditer(str(seq[start:stop])):
            pos_list.append(m.start()+start)
        
        cut_size = len(recognition_seq[enzyme])
           
        for i in range(len(pos_list)-1):
            j = i + 1
            
            l_start = pos_list[i]
            r_stop = pos_list[j]+cut_size 
            frag_len = r_stop - l_start
            
            if (frag_len>=oligo):
                l_stop = l_start+oligo
                r_start = r_stop-oligo
                
                l_tup = (l_start, l_stop, l_start, r_stop)
                r_tup = (r_start, r_stop, l_start, r_stop)
                l_seq = seq[l_start:l_stop]
                r_seq = seq[r_start:r_stop]
                
                self.oligo_seqs['{}:{}-L'.format(chr_name,
                                                 '-'.join(map(str, l_tup)))
                               ] = str(l_seq)
                if frag_len>oligo:
                    self.oligo_seqs['{}:{}-R'.format(chr_name,
                                                     '-'.join(map(str, r_tup)))
                                   ] = str(r_seq)
            else:
                print('The fragment {}:{}-{} is too small to design oligos '
                      'in. Skipping.'.format(chr_name, l_start, r_stop),
                      file=sys.stderr)
        
        print('\t...complete.')
        if __name__ != '__main__':
            print('Oligos stored in the oligo_seqs attribute')
        
        return self
    
    def gen_oligos_contig(self, chrom, region='', step=70, oligo=70):
        """Designs adjacent oligos based on a user-defined step size,
        across a specified region of a chromosome, or for the entire
        chromosome.
        
        Parameters
        ----------
        chrom : str
            Chromosome number/letter e.g. 7 or X
        region : str, optional
            The region of the chromosome to design oligos, e.g.
            10000-20000; omit this option to design oligos over the
        step : int, optional
            The step size, or how close adjacent oligos should be, default=70;
            for end-to-end oligos, set `step` to equal `oligo`
        oligo : int, optional
            The length of the oligos to design (bp), default=70
            
        Raises
        ------
        ValueError
            If `step` or `oligo` <1 or not an integer
            
        Returns
        -------
        self : object
        
        """
        
        check_value((step, oligo), ('Step size', 'Oligo size'))
        
        chr_name = 'chr'+str(chrom)
        
        print('Loading reference fasta file...')
        seq_dict = SeqIO.to_dict(SeqIO.parse(self.fa, 'fasta'))
        seq = seq_dict[chr_name].seq.upper()
        print('\t...complete\nGenerating oligos...')
            
        if not region:
            start = 0; stop = len(seq)
        else:
            start, stop = map(int, region.split('-'))
        
        self.oligo_seqs = {}
        
        final_start = stop - oligo
    
        while start<=final_start:
            stop = start + oligo
            ol_seq = str(seq[start:stop])
            self.oligo_seqs['{}:{}-{}-000-000-X'.format(chr_name,
                                                        start,
                                                        stop)] = ol_seq
            start += step  
        
        print('\t...complete.')
        if __name__ != '__main__':
            print('Oligos stored in the oligo_seqs attribute')
        
        return self
    
class OffTarget(Tools):
    """Designs oligos adjacent to potential CRISPR off-target sites"""
    
    __doc__ += Tools.__doc__
    
    def gen_oligos(self, bed, oligo=70, step=10, max_dist=200):
        r"""Designs oligos adjacent to user-supplied coordinates for
        potential CRISPR off-target cleavage sites
        
        Parameters
        ----------
        bed : str
            Path to tab-delimited bed file containing a list of coordinates
            for viewpoints in the capture experiment; must be in the format
            'chr'\\t'start'\\t'stop'\\t'name'\\n
        oligo : int, optional
            The length of the oligo to design (bp), default=70
        step : int, optional
            The step size, or how close adjacent oligos should be,
            default=10; for end-to-end oligos, set `step` to equal `oligo`
        max_dist : int, optional
            The maximum distance away from the off-target site to design
            oligos to, default = 200
        
        Returns
        -------
        self : object
        
        """
        
        check_value((step, oligo, max_dist),
                    ('Step size', 'Oligo size', 'Maximum distance'))
        
        print('Loading reference fasta file...')
        seq_dict = SeqIO.to_dict(SeqIO.parse(self.fa, 'fasta'))
        print('\t...complete\nGenerating oligos...')
    
        oligo_num = math.floor((max_dist-oligo)/step)
        
        with open(bed) as w:
            for x in w:
                chr_name, start, stop, name = x.strip().split('\t')
                
                if '_' in chr_name: continue
                
                chr_length = len(seq_dict[chr_name])
                start, stop = map(int, (start, stop))
                seq = seq_dict[chr_name].seq.upper()
                
                l_stop = start-10
                r_start = stop+10
            
                counter=1
                while counter<=oligo_num:
                    
                    l_start = l_stop-oligo
                    l_coor = '{}:{}-{}'.format(chr_name, l_start, l_stop)
                    r_stop = r_start+oligo
                    r_coor = '{}:{}-{}'.format(chr_name, r_start, r_stop)
                    
                    if l_start<0:
                        print('Oligo {} for off-target site {} could not be '
                              'generated because it went beyond the start of '
                              'the chromosome'.format(l_coor, name),
                        file=sys.stderr)
                    else:
                        l_seq = seq[l_start:l_stop]
                        self.oligo_seqs['{}-000-000-X'.format(l_coor)] = str(
                            l_seq)
                        
                    if r_stop>chr_length:
                        print('Oligo {} for off-target site {} could not '
                              'be generated because it went beyond the end of '
                              'the chromosome'.format(r_coor, name),
                        file=sys.stderr)
                    else:
                        r_seq = seq[r_start:r_stop]
                        self.oligo_seqs['{}-000-000-X'.format(r_coor)] = str(
                            r_seq)
                    
                    self._assoc[l_coor] = self._assoc[r_coor] = name
                    
                    l_stop-=step
                    r_start+=step
                    counter+=1
        
        print('\t...complete.')
        if __name__ != '__main__':
            print('Oligos stored in the oligo_seqs attribute')
        
        return self

if __name__ == '__main__':
    class_tup = ('Capture', 'Tiled', 'OffTarget')
    try:
        class_arg = sys.argv[1]
        if class_arg not in class_tup:
            raise NameError('{} is not a recognised class name, choose from '
                            'one of the following: {}'.format(
                                class_arg,
                                ', '.join(class_tup)
                            ))
    except IndexError:
        raise IndexError('design.py must be followed by one of the following '
                         'class names: {}'.format(', '.join(class_tup)))
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
        choices = ['mm9', 'mm10', 'hg18', 'hg19', 'hg38'],
        help = 'Genome build',
        required = True,
    )
    
    if class_arg == 'Capture': 
        parser.add_argument(
            '-b',
            '--bed',
            type = str,
            help = 'Path to bed file with capture viewpoint coordinates',
            required = True,
        )
        parser.add_argument(
            '-e',
            '--enzyme',
            type = str,
            choices = ['DpnII', 'NlaIII', 'HindIII'],
            help = 'Name of restriction enzyme, default=DpnII',
            default = 'DpnII',
            required = False,
        )
    elif class_arg == 'Tiled': 
        parser.add_argument(
            '-c',
            '--chr',
            type = str,
            help = 'Chromosome number/letter on which to design the oligos.',
            required = True,
        )
        parser.add_argument(
            '-r',
            '--region',
            type = str,
            help = 'The region in which to design the oligos; must be in the' \
                   ' format \'start-stop\' e.g. \'10000-20000\'. Omit this ' \
                   'option to design oligos across the entire chromosome.',
            required = False,
        )
        parser.add_argument(
            '--contig',
            action = 'store_true',
            help = 'Run in contiguous mode (restriciton enzyme independent).',
            required = False,
        )
        parser.add_argument(
            '-e',
            '--enzyme',
            type = str,
            choices = ['DpnII', 'NlaIII', 'HindIII'],
            help = 'Name of restriction enzyme, default=DpnII. Omit this ' \
                   'option if running in contiguous mode (--contig)',
            default = 'DpnII',
            required = False,
        )
        parser.add_argument(
            '-t',
            '--step_size',
            type = int,
            help = 'Step size (in bp) between adjacent oligos when running ' \
                   'in contiguous mode (--contig), default=70. Omit this option if ' \
                   'you are not using the --contig flag',
            default = 70,
            required = False,
        )
    elif class_arg == 'OffTarget':
        parser.add_argument(
            '-b',
            '--bed',
            type = str,
            help = 'Path to bed file with off-target coordinates',
            required = True,
        )
        parser.add_argument(
            '-t',
            '--step_size',
            type = int,
            help = 'Step size (in bp) between adjacent oligos, default=10',
            default = 10,
            required = False,
        )
        parser.add_argument(
            '-m',
            '--max_dist',
            type = int,
            help = 'The maximum distance away from the off-target site to ' \
                   'design oligos to, default=200',
            default = 200,
            required = False,
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
    
    args = parser.parse_args(sys.argv[2:])
    
    if not args.blat and not args.star_index:
        msg = '-s/--star_index argument is required if --blat is not selected'
        parser.error(msg)
    
    if class_arg == 'Capture':
        c = Capture(genome=args.genome, fa=args.fasta, blat=args.blat)
        c.gen_oligos(
            bed = args.bed,
            enzyme = args.enzyme,
            oligo = args.oligo,
        )
    elif class_arg == 'Tiled':
        c = Tiled(genome=args.genome, fa=args.fasta, blat=args.blat)
        if args.contig:
            c.gen_oligos_contig(
                chrom = args.chr,
                region = args.region,
                step = args.step_size,
                oligo = args.oligo
            )
        else:
            c.gen_oligos_capture(
                chrom = args.chr,
                region = args.region,
                enzyme = args.enzyme,
                oligo = args.oligo
            )
    elif class_arg == 'OffTarget':
        c = OffTarget(genome=args.genome, fa=args.fasta, blat=args.blat)
        c.gen_oligos(
            bed = args.bed,
            step = args.step_size,
            max_dist = args.max_dist,
            oligo = args.oligo,
        )
        
    c.write_oligos()
    if not args.test_fasta:    
        c.align_to_genome(s_idx=args.star_index)
        c.calculate_density()
    

