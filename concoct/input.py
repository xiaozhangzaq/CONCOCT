import re
import logging

import numpy as np
import pandas as p

from itertools import product, tee, izip

from Bio import SeqIO

def load_composition(comp_file,kmer_len,threshold):
        #Composition
        #Generate kmer dictionary
        feature_mapping, nr_features = generate_feature_mapping(kmer_len)
        #Count lines in composition file
        count_re = re.compile("^>")
        seq_count = 0
        with open(comp_file) as fh:
            for line in fh:
                if re.match(count_re,line):
                    seq_count += 1
    
        #Initialize with ones since we do pseudo count, we have i contigs as rows
        #and j features as columns
        composition = np.ones((seq_count,nr_features))
        
        
        contigs_id = []
        for i,seq in enumerate(SeqIO.parse(comp_file,"fasta")):
            contigs_id.append(seq.id)
            for kmer_tuple in window(seq.seq.tostring().upper(),kmer_len):
                composition[i,feature_mapping["".join(kmer_tuple)]] += 1
        composition = p.DataFrame(composition,index=contigs_id,dtype=float)
    
        # save contig lengths, used for pseudo counts in coverage
        contig_lengths = composition.sum(axis=1)
    
        #Select contigs to cluster on
        threshold_filter = composition.sum(axis=1) > threshold
        
        #log(p_ij) = log[(X_ij +1) / rowSum(X_ij+1)]
        composition = np.log(composition.divide(composition.sum(axis=1),axis=0))
        
        logging.info('Successfully loaded composition data.')
        return composition,contig_lengths,threshold_filter

def load_coverage(cov_file,cov_range,contig_lengths,normalize=False):
        #Coverage import, file has header and contig ids as index
        #Assume datafile is in coverage format without pseudo counts
        cov = p.read_table(cov_file,header=0,index_col=0)
        if cov_range is None:
            cov_range = (cov.columns[0],cov.columns[-1])

        # Adding pseudo count
        cov.ix[:,cov_range[0]:cov_range[1]] = cov.ix[:,cov_range[0]:cov_range[1]].add(
                (100/contig_lengths),
                axis='index')

        if normalize:
            # Normalize
            cov.ix[:,cov_range[0]:cov_range[1]] = \
              cov.ix[:,cov_range[0]:cov_range[1]].divide(
                 cov.ix[:,cov_range[0]:cov_range[1]].sum(axis=1),axis=0)
        else:
            # Log transform
            cov.ix[:,cov_range[0]:cov_range[1]] = np.log(
                cov.ix[:,cov_range[0]:cov_range[1]])
    
        logging.info('Successfully loaded coverage data.')
        return cov,cov_range
    

def generate_feature_mapping(kmer_len):
    BASE_COMPLEMENT = {"A":"T","T":"A","G":"C","C":"G"}
    kmer_hash = {}
    counter = 0
    for kmer in product("ATGC",repeat=kmer_len):
        kmer = ''.join(kmer)
        if kmer not in kmer_hash:
            kmer_hash[kmer] = counter
            rev_compl = ''.join([BASE_COMPLEMENT[x] for x in reversed(kmer)])
            kmer_hash[rev_compl] = counter
            counter += 1
    return kmer_hash, counter+1

def window(seq,n):
    els = tee(seq,n)
    for i,el in enumerate(els):
        for _ in xrange(i):
            next(el, None)
    return izip(*els)