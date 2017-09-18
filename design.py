#!/usr/bin/env python

from __future__ import print_function, division

import argparse
import math
import re
import sys

import numpy as np  # >=1.7

from oligo.tools import Tools

recognition_seq = {'DpnII': 'GATC',
                   'NlaIII': 'CATG',
                   'HindIII': 'AAGCTT'}

def check_value(values, labels):
    for value, label in zip(values, labels):
        if (value<1) | isinstance(value, float):
            raise ValueError(
                '{} must be an integer greater than 0'.format(label))
            break
    else:
        return None

#def create_key(chrom, frag_coor, side, frag=False, *oligo_coor):
#    if frag:
#        key = ':'.join((chrom, '-'.join(map(str, (oligo_coor + frag_coor)))))
#        key = '-'.join((key, side))
#    
#        return key
#    else:
#        return (':'.join((chrom, '-'.join(map(str, x + frag_coor + (side,))))) for x in oligo_coor)
def create_key_frag(chrom, oligo_coor, frag_coor, side):
    key = ':'.join((chrom, '-'.join(map(str, (oligo_coor + frag_coor)))))
    key = '-'.join((key, side))
            
    return key

def get_sequence(seq, *args):
    return (str(seq[x[0]:x[1]]) for x in args)  # returns a generator so that all sequences outside of the dictionary are not retained in the memory

def create_key(chrom, *args):
    return (':'.join((chrom, '-'.join((map(str, x + ('000','000','X')))))) for x in args)

class FragmentError(Exception):
    pass

class FragmentMixin(object):
    
    def _get_fragment_seqs(self, chrom, start, stop, chrom_seq=''):
        frag_length = stop - start
        if frag_length < self.oligo:
            raise FragmentError('{} is too small to design oligos in. Skipping.')
        
        left_coor = (start, start + self.oligo)
        right_coor = (stop - self.oligo, stop)
        frag_coor = (start, stop)
        
        left_key = create_key_frag(chrom, left_coor, frag_coor, 'L')
        right_key = create_key_frag(chrom, right_coor, frag_coor, 'R')
        
        if left_key in self.oligo_seqs:
            raise FragmentError('{} is redundant to another position. Skipping.')
        
        if not chrom_seq: chrom_seq = self.genome_seq[chrom].seq.upper()
        left_seq, right_seq = get_sequence(chrom_seq, *(left_coor, right_coor))
        
        self.oligo_seqs[left_key] = left_seq     
        if frag_length > self.oligo: self.oligo_seqs[right_key] = right_seq
        
        return None

class Capture(Tools, FragmentMixin):
    """Designs oligos for Capture-C"""
    
    __doc__ += Tools.__doc__
        
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
        self._create_attr(oligo)
        
        cut_sites = {}
        cut_size = len(recognition_seq[enzyme])
        rec_seq = re.compile(recognition_seq[enzyme])
        
        print('Generating oligos...')
        for chrom, attr in self.genome_seq.items():
            chrom_seq = str(attr.seq).upper()
            cut_sites[chrom] = [cut_site.start() for cut_site
                                in rec_seq.finditer(chrom_seq)]
            cut_sites[chrom] = np.array(cut_sites[chrom])
            
        with open(bed) as viewpoints:
            for vp in viewpoints:
                chrom, vp_start, vp_stop, name = vp.strip().split('\t')
                
                if '_' in chrom: continue
                
                vp_start = int(vp_start)
                frag_start = cut_sites[chrom][cut_sites[chrom] <= vp_start][-1]
                frag_stop = cut_sites[chrom][cut_sites[chrom] >= vp_start][0] + cut_size # currently this picks an adjacent fragment if the site is in a cutsite; are we okay with that?
                
                try:
                    self._get_fragment_seqs(chrom, frag_start, frag_stop)
                except FragmentError as e:
                    frag_id = '{}:{}-{} ({}) is in a fragment that'.format(
                        chrom, vp_start, vp_stop, name)
                    print(str(e).format(frag_id), file=sys.stderr)
                    continue
                
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
    
class Tiled(Tools, FragmentMixin):
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
        self._create_attr(oligo)
        
        if 'chr' not in str(chrom): chrom = ''.join(('chr'+str(chrom)))
        chrom_seq = self.genome_seq[chrom].seq.upper()
            
        start, stop = (0, len(chrom_seq)) if not region else map(int, region.split('-'))
        
        rec_seq = re.compile(recognition_seq[enzyme])
        cut_size = len(recognition_seq[enzyme])
        cut_sites = [cut_site.start()+start for cut_site in rec_seq.finditer(str(chrom_seq[start:stop]))]
        
        print('Generating oligos...')   
        for i in range(len(cut_sites)-1):
            j = i + 1
            
            frag_start = cut_sites[i]
            frag_stop = cut_sites[j]+cut_size 
            
            try:
                self._get_fragment_seqs(chrom, frag_start, frag_stop, chrom_seq=chrom_seq)
            except FragmentError as e:
                frag_id = 'The fragment {}:{}-{}'.format(chrom, frag_start, frag_stop)
                print(str(e).format(frag_id), file=sys.stderr)
                continue
                
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
        self._create_attr(oligo)
        
        if 'chr' not in chrom: chrom = ''.join(('chr'+str(chrom)))
        chrom_seq = self.genome_seq[chrom].seq.upper()
            
        start, stop = (0, len(chrom_seq)) if not region else map(int, region.split('-'))
        stop = stop - oligo
        
        print('Generating oligos...')
        coors = [(x, x + oligo) for x in range(start, stop, step)]
        sequences = get_sequence(seq, *coors)  # this method is better than the line below because the sequences do not have be exploded from their individuals lists before being stored in the dictionary
        #sequences = [get_sequence(seq, *(x,)) for x in coors]  # slightly faster
        keys = create_key(chrom, *coor)
        #keys = [create_key(chrom, x, ('000', '000'), 'X') for x in coors]
        self.oligo_seqs = dict(zip(keys, sequences))
        
        print('\t...complete.')
        if __name__ != '__main__':
            print('Oligos stored in the oligo_seqs attribute')
        
        return self
    
    def __str__(self):
        
        return 'Tiled Capture oligo design object for the {} genome'.format(
            self.genome)
    
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
        self._create_attr(oligo)
    
        oligo_num = math.floor((max_dist-oligo)/step)
        
        with open(bed) as crispr_sites:
            for cs in crispr_sites:
                chrom, start, stop, name = cs.strip().split('\t')
                
                if '_' in chrom: continue
                  
                start, stop = map(int, (start, stop))
                chrom_seq = self.genome_seq[chrom].seq.upper()
                chrom_length = len(chrom_seq)
                
                exc_start = start-10
                exc_stop = stop+10
                
                upstream = [(x-oligo, x) for x in
                    range(start-max_dist+oligo, exc_start+1, step)
                    if x-oligo>=0]
                downstream = [(x, x+oligo) for x in
                    range(exc_stop, stop+max_dist-oligo+1, step)
                    if x+oligo<=chrom_length]
                all_coors = upstream+downstream
                sequences = get_sequence(chrom_seq, *all_coors)
                keys = list(create_key(chrom, *all_coors))
                self.oligo_seqs.update(zip(keys, sequences))
                self._assoc.update({x: name for x in keys})
        
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
        
    c.write_fasta()
    if not args.test_fasta:    
        c.detect_repeats().align_to_genome(s_idx=args.star_index)
        c.extract_repeats().calculate_density().write_oligo_info()
    

