import chess
import os
import math

import numpy as np

SFEN_BIN_SIZE = 40
HUFFMAN_TABLE = [
    (0b0000, 1, None),
    (0b0001, 4, chess.PAWN),
    (0b0011, 4, chess.KNIGHT),
    (0b0101, 4, chess.BISHOP),
    (0b0111, 4, chess.ROOK),
    (0b1001, 4, chess.QUEEN)
]

def read_bit(data, cursor):
    b = (data[cursor//8] >> (cursor&7))&1;
    cursor += 1
    return b, cursor


def read_bits(data, cursor, nbits):
    v = 0
    for k in range(nbits):
        b, cursor = read_bit(data, cursor)
        if b > 0:
            v |= (1 << k)
    return v, cursor


def read_piece(data, cursor):
    found = False
    code = 0
    nbits = 0
    piece_type = None
    while not found:
        b, cursor = read_bit(data, cursor)
        code |= (b << nbits)
        nbits += 1
        
        for k in range(6):
            if HUFFMAN_TABLE[k][0] == code and HUFFMAN_TABLE[k][1] == nbits:
                found = True
                piece_type = HUFFMAN_TABLE[k][2]
                break

    if not piece_type:
        return piece_type, cursor

    b, cursor = read_bit(data, cursor)
    if b == 0:
        color = chess.WHITE
    else:
        color = chess.BLACK

    return chess.Piece(piece_type, color), cursor


def read_position(data):
    cursor = 0
    board = chess.Board(fen=None)

    # Side to move
    b, cursor = read_bit(data, cursor)
    if b == 0:
        board.turn = chess.WHITE
    else:
        board.turn = chess.BLACK

    # King positions
    wksq, cursor = read_bits(data, cursor, 6)
    board.set_piece_at(wksq, chess.Piece(chess.KING, chess.WHITE))
    bksq, cursor = read_bits(data, cursor, 6)
    board.set_piece_at(bksq, chess.Piece(chess.KING, chess.BLACK))

    # Piece positions
    for r in range(8)[::-1]:
        for f in range(8):
            sq = chess.square(f, r)
            if sq == wksq or sq == bksq:
                continue

            piece, cursor = read_piece(data, cursor)
            if piece:
                board.set_piece_at(sq, piece)

    # Castling availability
    b, cursor = read_bit(data, cursor)
    if b == 1:
        board.castling_rights |= chess.BB_H1
    b, cursor = read_bit(data, cursor)
    if b == 1:
        board.castling_rights |= chess.BB_A1
    b, cursor = read_bit(data, cursor)
    if b == 1:
        board.castling_rights |= chess.BB_H8
    b, cursor = read_bit(data, cursor)
    if b == 1:
        board.castling_rights |= chess.BB_A8

    # En-passant square
    b, cursor = read_bit(data, cursor)
    if b == 1:
        board.ep_square, cursor = read_bits(data, cursor, 6)

    # 50-move counter, low-bits
    low50, cursor = read_bits(data, cursor, 6)

    # Fullmove counter
    low_full, cursor = read_bits(data, cursor, 8)
    high_full, cursor = read_bits(data, cursor, 8)
    board.fullmove_number = (high_full << 8) | low_full

    # 50-move counter, high-bits
    high50, cursor = read_bit(data, cursor)
    board.halfmove_clock = (high50 << 6) | low50

    return board


# bit  0- 5: destination square (from 0 to 63)
# bit  6-11: origin square (from 0 to 63)
# bit 12-13: promotion piece type - 2 (from KNIGHT-2 to QUEEN-2)
# bit 14-15: special move flag: promotion (1), en passant (2), castling (3)
def read_move(data):
    to_sq = int(data & 0x003F)
    from_sq = int((data >> 6) & 0x003F)
    promotion = int((data >> 12) & 0x0003)
    special = (data >> 14) & 0x0003

    if special == 1:
        move = chess.Move(from_sq, to_sq, promotion+2)
    else:
        move = chess.Move(from_sq, to_sq)

    return move


class NNUEBinReader:
    def __init__(self, path, **args):
        self.path = path
        self.offset = args.get('offset', 0)
        self.nsamples = os.path.getsize(path)//SFEN_BIN_SIZE
        self.fh = open(path, 'rb')
        self.fh.seek(self.offset)


    def close(self):
        self.fh.close()


    def get_num_samples(self):
        return self.nsamples


    def get_sample(self):
        # Read the first 32 bytes which describe the position
        data = np.fromfile(self.fh, dtype='uint8', count=32)
        board = read_position(data)

        # Read the next two bytes which is the score
        score = int(np.fromfile(self.fh, dtype='int16', count=1))

        # Read the next two bytes which is the move
        data = np.fromfile(self.fh, dtype='uint16', count=1)
        move = read_move(data)

        # Read the next two bytes which is the ply count
        ply = int(np.fromfile(self.fh, dtype='uint16', count=1))
    
        # Read the next byte which is the result
        result = np.fromfile(self.fh, dtype='int8', count=1)

        # Read and skip one byte which is just padding
        np.fromfile(self.fh, dtype='uint8', count=1)

        return (board, score, move, ply, result)


    def get_raw_sample(self):
        # Read the first 32 bytes which describe the position
        raw_pos = np.fromfile(self.fh, dtype='uint8', count=32)

        # Read the score
        raw_score = np.fromfile(self.fh, dtype='int16', count=1)

        # Read the move
        raw_move = np.fromfile(self.fh, dtype='uint16', count=1)

        # Read the ply count
        raw_ply = np.fromfile(self.fh, dtype='uint16', count=1)

        # Read the the result
        raw_result = np.fromfile(self.fh, dtype='int8', count=1)

        # Read and skip one byte which is just padding
        np.fromfile(self.fh, dtype='uint8', count=1)

        return (raw_pos, raw_score, raw_move, raw_ply, raw_result)


    def parse_position(self, data):
        return read_position(data)


    def parse_move(self, data):
        return read_move(data)
