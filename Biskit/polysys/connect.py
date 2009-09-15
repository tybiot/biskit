##
## Biskit, a toolkit for the manipulation of macromolecular structures
## Copyright (C) 2004-2009 Raik Gruenberg & Johan Leckner
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
## General Public License for more details.
##
## You find a copy of the GNU General Public License in the file
## license.txt along with this program; if not, write to the Free
## Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
##
##
## last $Author: graik $
## last $Date: 2009-07-02 17:36:36 +0200 (Thu, 02 Jul 2009) $
## $Revision: 810 $

import os.path as osp
from Biskit import PDBModel, BiskitError, PDBError
import Biskit.tools as T
## from Biskit.Residue import Residue ## experimental
import numpy as N

class FusionError( BiskitError ):
    pass


class Fusion( object ):
    
    adapters = \
        { 'helix'   : T.dataRoot('poly/fusion/adapter_helix.model'),
          'sheet'   : T.dataRoot('poly/fusion/adapter_sheet.model'),
          'extended': T.dataRoot('poly/fusion/adapter_extended.model')
          }
    
    adapter_root = T.dataRoot('/polysys/fusion/')
    
    def __init__( self, adapter='extended' ):
        """
        Create new fusion object.
        @param adapter: adapter type to use for fusion peptide bond orientation.
                        (one of: 'helix', 'sheet', 'extended'(default)) or
                        custom PDBModel with two residues.
        @type  adapter: str OR PDBModel
        """
        try:
            if type( adapter ) is str and not osp.isfile( adapter ) :
                self.adapter_model = PDBModel( self.adapters[ adapter ] )
            elif type( adapter ) is str and osp.isfile( adapter ):
                self.adapter_model = PDBModel( adapter )
            elif isinstance( adapter, PDBModel ):
                self.adapter_model = adapter
            else:
                raise FusionError, 'invalid adapter argument: %r' % adapter

        except PDBError, why:
            raise FusionError, 'cannot load adapter: %r' % why
    

    def select_atoms( self, m, rindex=0, names=[''] ):
        """
        Select atoms within a single residue of model <m>.
        @return: N.array of int, atom indices within residue <rindex> in same 
                 order as atom <names>
        """
        a_indices, ri = m.res2atomIndices( [rindex] )
        
        ## map atom names to atom indices
        name2i = dict( zip( [ m['name'][i] for i in a_indices ],
                          a_indices ) )
        
        ## return atom indices in same order as atom names input
        r = [ name2i[name] for name in names if name in name2i ]
        
        return N.array(r)
       
        
    def remove_atoms( self, m, rindex=-1, names=['O', 'OT1', 'OT2', 'OXT'] ):
        """
        Remove atoms with given name from given residue.
        """     
        a_indices = self.select_atoms( m, rindex, names )
        m.remove( a_indices )

    def fitOverlap( self, m1, m2, r1=-1, r2=0, names=['N', 'CA', 'C'] ):
        """
        Transform model m2 so that some atoms selected from residue r2 fit
        on the corresponding atoms of m1's residue r1.
        @return: PDBModel, transformed m2
        """
        sel_m1 = self.select_atoms( m1, rindex= r1, names= names )
        sel_m2 = self.select_atoms( m2, rindex= r2, names= names )

        ref = m1.take( sel_m1 )
        probe = m2.take( sel_m2 )
        
        rt = probe.transformation( ref )        
        return m2.transform( rt )
        
    
    def fuseN2C( self, m1, m2 ):
        """
        Fuse C-terminal of m1 to N-terminal of m2.
        @param m1: PDBModel, first protein
        @param m2: PDBModel, second protein
        """
        m1 = m1.clone()
        m2 = m2.clone()
        
        self.remove_atoms( m1, rindex=-1, names=['O', 'OT1', 'OT2', 'OXT'] )
        self.remove_atoms( m2, rindex=0,  names=['H', 'HT1', 'HT2', 'HT3'] )
        
        ## fit adapter to C-terminal of model 1
        adapter = self.adapter_model
        adapter = self.fitOverlap( m1, adapter, r1=-1, r2=0, 
                                   names=['N', 'CA', 'C', 'CB'] ) ## note: not general
        
        adapter.writePdb( '~/adapter.pdb' )
        
        ## fit N terminal model2 to C terminal of adapter
        m2 = self.fitOverlap( adapter, m2, r1=-1, r2=0, names=['N', 'CA', 'C', 'O'] )
        
        ## concatenate models
        assert( isinstance( m1, PDBModel ) )
        r = m1.concat( m2 )
        r['chain_id'] = [ r['chain_id'][0] ] * len( r )
        r.renumberResidues()
        
        return r
    
if __name__ == '__main__':
    
    m1 = PDBModel( T.testRoot( 'polysys/fusion_1.pdb' ) )
    m2 = PDBModel( T.testRoot( 'polysys/fusion_2.pdb' ) )
    
    f = Fusion( adapter='helix' )
    r = f.fuseN2C( m1, m2 )
    
    r.writePdb('~/fuse.pdb' )