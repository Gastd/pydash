from r2a.ir2a import IR2A
from player.parser import *


class R2AMedia(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)

        self.vazoes = []
        self.qi = []
        pass
        

    def handle_xml_request(self, msg):

        self.send_down(msg)

    def handle_xml_response(self, msg):
        print('>>>>>>>>>>>> A MENSAGEM!')
        print('PARSEEEEEEEEEEE')
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        print(parsed_mpd.get_qi()[10])
        self.send_up(msg)

    def handle_segment_size_request(self, msg):

        msg.add_quality_id(self.qi[9])

        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
