from typing import TextIO, BinaryIO, override
from heapq import heappop, heappush
from bitarray import bitarray

from .interface import CompressionMethod, CompressionMethodError


class HuffmanTreeNode:
    """Represents a node in a huffman tree"""

    def __init__(
        self,
        char: str,
        freq: int,
        left: "HuffmanTreeNode | None" = None,
        right: "HuffmanTreeNode | None" = None,
    ) -> None:
        """
        Args:
            char (str): Character (if leaf node) or multiple characters which this node represents.
            freq (int): The frequency of occurences of this character (if leaf node), or the sum
            of the child nodes' characters' frequencies.
            left (HuffmanTreeNode | None, optional): The left node with the smaller frequency,
            or None. Defaults to None.
            right (HuffmanTreeNode | None, optional): The right node with the higher frequency,
            or None. Defaults to None.
        """

        self.left = left
        self.right = right
        self.freq = freq
        self.char = char
        self.code = bitarray()

    def code_tree(self, code: bitarray | None = None) -> None:
        """Assign binary codes to self and recursively to every child node in the tree.

        Args:
            code (bitarray | None, optional): The code to assign to this node. Defaults to None.
        """
        code = code or bitarray()
        self.code = code

        if self.left and self.right:
            self.left.code_tree(code + [1])
            self.right.code_tree(code + [0])

    def __lt__(self, other: "HuffmanTreeNode") -> bool:
        return self.freq < other.freq

    def __le__(self, other: "HuffmanTreeNode") -> bool:
        return self.freq <= other.freq

    @override
    def __str__(self, indent: str = "") -> str:
        output: str = f"{indent} ({self.char} {self.freq} {self.code})"
        indent += 4 * " "
        if self.left:
            output += "\n" + self.left.__str__(indent)
        if self.right:
            output += "\n" + self.right.__str__(indent)

        return output


class Huffman(CompressionMethod):
    """Implements the Huffman compression algorithm as a CompressionMethod."""

    def _build_huffman_tree(
        self, freq_list: list[tuple[int, str]]
    ) -> HuffmanTreeNode | None:
        """Constructs a huffman tree from a list of tuples,
        containing a character and its frequency, ordered by the frequencies.

        Args:
            freq_list (list[tuple[int, str]]): list of tuples, containing
            the frequency and the character.

        Returns:
            HuffmanTreeNode | None: The huffman tree built, or None,
            if no characters given in freq_list.
        """
        if len(freq_list) == 0:
            return None

        nodes: list[HuffmanTreeNode] = []

        # Init forest with single node "trees"
        for freq, char in freq_list:
            heappush(nodes, HuffmanTreeNode(char, freq, None, None))

        # Merge trees until only one tree is left, i.e. the huffman tree.
        # Trees are merged by taking the two trees with the smallest
        # frequencies and merging them into one tree.
        while len(nodes) > 1:
            # Left popped first as it is smaller than right in huffman tree
            left, right = heappop(nodes), heappop(nodes)
            heappush(
                nodes,
                HuffmanTreeNode(
                    left.char + right.char, left.freq + right.freq, left, right
                ),
            )

        huffman_tree = heappop(nodes)

        return huffman_tree

    def _count_frequencies(self, text: TextIO) -> list[tuple[int, str]]:
        """Count the number of occurences for each character in given input.

        Args:
            text (TextIO): Object containing the text from which to count character frequencies.

        Returns:
            list[tuple[int, str]]: Returns a list of tuples, containing each character's
            frequency and the respective character.
        """
        freq_dict: dict[str, int] = {}

        for c in text.read():
            freq_dict[c] = freq_dict.get(c, 0) + 1

        freq_list: list[tuple[int, str]] = []
        for c, f in freq_dict.items():
            freq_list.append((f, c))

        freq_list.sort(reverse=True)

        return freq_list

    def _get_codes(self, huffman_tree: HuffmanTreeNode) -> dict[str, bitarray | None]:
        """Compute the huffman codes for each character in the given Huffman tree.

        Args:
            huffman_tree (HuffmanTreeNode): The huffman tree based on which
            to construct Huffman codes.
        Returns:
            dict[str, bitarray | None]: _description_
        """
        huffman_tree.code_tree()

        codes: dict[str, bitarray | None] = {}

        def traverse(node: HuffmanTreeNode, code: bitarray | None = None):
            if code is None:
                code = bitarray()

            if node.left and node.right:
                traverse(node.left, code + [0])
                traverse(node.right, code + [1])
            else:  # If leaf node, assign code and stop traversing
                codes[node.char] = code

        traverse(huffman_tree)
        return codes

    def _encode_text(
        self, text: TextIO, huffman_codes: dict[str, bitarray | None]
    ) -> bitarray:
        """Encodes the given string using the given huffman codes.

        Args:
            text (TextIO): The text to encode

            huffman_codes (dict[str, bitarray  |  None]):
            The huffman codes to be used for text encoding. Preferably the codes that were
            generated for the same text provided for best compression and no missing codes.

        Raises:
            ValueError: If the provided Huffman tree misses characters used in the given text.

        Returns:
            bitarray: Encoded text.
        """
        result = bitarray()
        c = text.read(1)
        while c:
            code = huffman_codes[c]
            if code is None:
                raise ValueError(f"Huffman code for character {c} missing.")

            result += code
            c = text.read(1)

        return result

    def _encode_tree(self, huffman_tree: HuffmanTreeNode) -> bytes:
        """Compress the Huffman tree by encoding it into a byte format.

        Args:
            huffman_tree (HuffmanTreeNode): The Huffman tree to encode.

        Returns:
            bytes: Bytes representing the encoded Huffman tree.
        """

        def encode_tree(node: HuffmanTreeNode) -> bytes:
            # Either node is a leaf or it has two children. If not, something has gone wrong.
            if (node.left is None and node.right) or (node.left and node.right is None):
                raise ValueError(
                    "Broken Huffman tree: tree has a node with a single child."
                )

            # If node is a leaf. 'and' should be sufficient, but for static type checking 'or' used.
            if node.left is None or node.right is None:
                return b"1" + node.char.encode("utf-8")

            return b"0" + encode_tree(node.left) + encode_tree(node.right)

        return encode_tree(huffman_tree)

    def _decode_tree(self, tree_str: str) -> HuffmanTreeNode | None:
        """Decompress an encoded/compressed Huffman tree (by _encode_tree),
        into a HuffmanTreeNode object.

        Args:
            tree_str (str): The encoded tree.

        Returns:
            HuffmanTreeNode | None: The reconstructed Huffman tree, or None,
            if the tree does not exist.
        """

        def decode_tree(
            tree_str: str, depth: int = 0
        ) -> tuple[HuffmanTreeNode | None, str]:
            if not tree_str:
                return None, tree_str

            if tree_str[0] == "1":
                char = tree_str[1]
                return HuffmanTreeNode(char, 0), tree_str[2:]

            left, tree_str = decode_tree(tree_str[1:], depth + 1)
            right, tree_str = decode_tree(tree_str, depth + 1)
            return HuffmanTreeNode("", 0, left, right), tree_str

        tree, _remaining = decode_tree(tree_str)

        return tree

    def _decode_text(
        self, encoded_text: bitarray, huffman_tree: HuffmanTreeNode
    ) -> str:
        """Decompres compressed text using the given Huffman tree.

        Args:
            encoded_text (bitarray): Encoded text to be decoded.
            huffman_tree (HuffmanTreeNode): Huffman tree to be used for decoding the text.

        Returns:
            str: The resulting decoded text.
        """
        result: list[str] = []
        current_node = huffman_tree

        for bit in encoded_text:
            if bit == 0:
                current_node = current_node.left
            else:
                current_node = current_node.right

            if current_node is None:
                break

            if current_node.left is None and current_node.right is None:  # Leaf node
                result.append(current_node.char)
                current_node = huffman_tree  # Reset to root for next character

        return "".join(result)

    def _decode(self, tree_str: str, encoded_text: bitarray) -> str:
        huffman_tree = self._decode_tree(tree_str)
        if huffman_tree is None:
            raise ValueError("Invalid tree string")

        decoded_text = self._decode_text(encoded_text, huffman_tree)
        return decoded_text

    def _read_headers(self, bin_in: BinaryIO) -> tuple[int, int]:
        """Reads th headers from a BinaryIO object containing compressed text.

        Args:
            bin_in (BinaryIO): Object from which to read compressed text.

        Raises:
            CompressionMethodError: If compressed content is invalid.

        Returns:
            tuple[int, int]: A tuple containing the length of padding and the tree, in bytes.
        """
        # Header is 16 bytes long, see the compress method for how header is formed.
        header = bin_in.read(16)
        padding_len = int.from_bytes(bytes=header[:8], byteorder="big", signed=False)
        tree_len = int.from_bytes(bytes=header[8:], byteorder="big", signed=False)

        # Check that values are sensible
        # Tree length should be less than remaining length.
        # Padding is to make the length a multiple of 8 so it should be less than 8.
        if (
            padding_len < 0
            or tree_len < 0
            or padding_len >= 8
            or tree_len > len(bin_in.read())
        ):
            raise CompressionMethodError(
                "Invalid header: padding_len or tree_len out of bounds. "
                + "Make sure the file is a valid compressed file."
            )

        # Move pointer back to the start of the tree
        bin_in.seek(16, 0)

        return padding_len, tree_len

    # Interface methods
    @override
    def compress(self, text_in: TextIO, bin_out: BinaryIO) -> None:
        # Note: to allow more memory-efficient handling of larger files,
        # might want to consider using generators in some places.
        try:
            text_in.seek(0)
            freq_list = self._count_frequencies(text_in)
            text_in.seek(0)
            tree = self._build_huffman_tree(freq_list)
            if tree is None:
                return
            codes = self._get_codes(tree)

            encoded_text = self._encode_text(text_in, codes)

            encoded_tree = self._encode_tree(tree)

            if encoded_text is None:
                return

            # Prepare the header
            # Info fields are eight byte unsigned integers. The header is therefore 16 bytes long.
            # Also tree length is limited to 2^64, probably sufficient though.
            # Note: consider defining the header params in some constants
            tree_len = len(encoded_tree)
            tree_len_info = tree_len.to_bytes(length=8, byteorder="big", signed=False)

            padding_len_info = encoded_text.padbits.to_bytes(
                length=8, byteorder="big", signed=False
            )

            header = padding_len_info + tree_len_info

            bin_out.write(header)
            bin_out.write(encoded_tree)
            bin_out.write(encoded_text.tobytes())

        except UnicodeDecodeError as e:
            raise CompressionMethodError(
                f"Invalid file format. Must be {e.encoding} encoded."
            ) from e

    @override
    def decompress(self, bin_in: BinaryIO, text_out: TextIO) -> None:
        padding_len, tree_len = self._read_headers(bin_in)
        tree_str = bin_in.read(tree_len).decode("utf-8")
        encoded_text_bytes = bin_in.read()
        encoded_text_bits = bitarray()
        encoded_text_bits.frombytes(encoded_text_bytes)

        # Remove padding
        if padding_len > 0:
            encoded_text_bits = encoded_text_bits[:-padding_len]
        decoded_text = self._decode(tree_str, encoded_text_bits)
        text_out.write(decoded_text)
