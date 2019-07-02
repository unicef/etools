import vcr

VCR = vcr.VCR(serializer='yaml',
              record_mode='once',
              match_on=['uri', 'method'],
              filter_headers=['authorization', 'token'],
              filter_post_data_parameters=['client_id', 'client_secret'],
              decode_compressed_response=True)
