NUM_SQ = 64
NUM_PT = 10
NUM_PLANES = NUM_SQ*NUM_PT
NUM_REAL_FEATURES = NUM_PLANES*NUM_SQ
NUM_VIRTUAL_FEATURES = NUM_PT*NUM_SQ

class Features:
    name = 'HalfKP'


    def get_num_inputs(self):
        ninputs = NUM_REAL_FEATURES
        return ninputs
