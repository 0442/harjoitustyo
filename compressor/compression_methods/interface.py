from abc import ABC, abstractmethod
from typing import TextIO, BinaryIO

class CompressionMethod(ABC):
  """ABC defining an interface for different text compression methods."""
  @abstractmethod
  def compress(self, input: TextIO, otuput: BinaryIO) -> None:
    """
    Parameters
    ----------
    input : TextIO
        TextIO object from which compressable text data is read.
    output : BinaryIO 
        BinaryIO object to which compressed output is written to.
    """
    ...

  @abstractmethod
  def uncompress(self, input: BinaryIO, output: TextIO) -> None:
    """
    Parameters
    ----------
    input : BinaryIO
        BinaryIO object from which compressed data is read.
    output : TextIO
        TextIO object to which uncompressed text output is written to.
    """
    ...