import logging
import numpy as np

from cloudvolume import CloudVolume

from chunkflow.chunk import Chunk
from chunkflow.lib.cartesian_coordinate import Cartesian
from .base import OperatorBase


class MaskOperator(OperatorBase):
    def __init__(self,
                 volume_path: str,
                 mask_mip: int,
                 chunk_mip: int,
                 inverse: bool = False,
                 fill_missing: bool = True,
                 name: str = 'mask'):
        super().__init__(name=name)

        self.mask_mip = mask_mip
        self.chunk_mip = chunk_mip
        self.inverse = inverse
        
        self.mask_vol = CloudVolume(volume_path,
                                    bounded=False,
                                    fill_missing=fill_missing,
                                    progress=False,
                                    parallel=1,
                                    mip=mask_mip)

        logging.info(f'build mask operator based on {volume_path} at mip {mask_mip}')
    
    def __call__(self, chunks: list):
        """ Make part of chunk to be black according to a mask chunk.
        Note that the operation is inplace and the data in the input chunk is changed.
        """
        if isinstance(chunks, Chunk):
            chunks = [chunks]
        elif len(chunks)>1: 
            for chunk in chunks:
                assert isinstance(chunk, Chunk)
                assert chunk.voxel_offset == chunks[0].voxel_offset
                assert chunk.voxel_size == chunks[0].voxel_size
        
        assert isinstance(chunks, list)
        assert len(chunks)>0

        voxel_size = chunks[0].voxel_size

        mask_voxel_size = Cartesian.from_collection(
            self.mask_vol.resolution[::-1]
        )
        factor = mask_voxel_size // voxel_size
        # factor = tuple(m//c for m, c in zip(self.mask_vol.resolution[::-1], chunk.voxel_size))
        for m, c in zip(mask_voxel_size, voxel_size): 
            assert m >= c
            assert m % c == 0

        mask_in_high_mip = self._read_mask_in_high_mip(chunks[0].bbox, factor)

        if np.alltrue(mask_in_high_mip == 0):
            logging.warning('the mask is all black, mask all the voxels directly')
            for chunk in chunks:
                np.multiply(chunk, 0, out=chunk)
            return chunks
        if np.all(mask_in_high_mip):
            logging.warning("mask elements are all positive, return directly")
            return chunks

        assert np.any(mask_in_high_mip)

        
        for chunk in chunks:
            # make it the same type with input
            mask_in_high_mip = mask_in_high_mip.astype(chunk.dtype)
            for offset in np.ndindex(factor):
                chunk.array[..., 
                            np.s_[offset[0]::factor[0]], 
                            np.s_[offset[1]::factor[1]],
                            np.s_[offset[2]::factor[2]]] *= mask_in_high_mip
        
        return chunks


    def _read_mask_in_high_mip(self, chunk_bbox, factor):
        """
        chunk_bbox: the bounding box of the chunk in lower mip level
        """
        # print("download mask chunk...")
        # make sure that the slices only contains zyx without channel
        chunk_slices = chunk_bbox.to_slices()[-3:]

        # only scale the indices in XY plane
        # only scale the indices in XY plane
        mask_slices = tuple(
            slice(a.start // f, a.stop // f)
            for a, f in zip(chunk_slices[-3:], factor))
        
        # the slices did not contain the channel dimension
        mask = self.mask_vol[mask_slices[::-1]]
        # this is a cloudvolume VolumeCutout rather than a normal numpy array
        # which will make np.alltrue(mask_in_high_mip == 0) to be
        # VolumeCutout(False) rather than False, so we need to transform it 
        # to numpy
        mask = mask.astype(bool)
        mask = np.asarray(mask)
        mask = np.transpose(mask)
        mask = np.squeeze(mask, axis=0)

        if self.inverse:
            mask = (mask == 0)
        return mask
