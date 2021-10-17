from r2a.ir2a import IR2A
from player.parser import *
import time


class R2Bandwith(IR2A):

    # ---------------- ATRIBUTOS ------------------------

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.lengthQuality = 0 # Inicializando o estado de qualidades
        self.durationMovie = 0

    # ------------------ Métodos -----------------------

    def saveLengthQuality(self, lengthToAdd):
        self.lengthQuality = lengthToAdd

    def saveDurationMovie(self, durationMovie):
        self.durationMovie = int(durationMovie['duration'])


    # ------------------ API ------------------------

    def handle_xml_request(self, msg): # Envio do pedido da requisição
        self.send_down(msg)

    def handle_xml_response(self, msg): # Tratamento da reposta Inicial

        self.parsed_mpd = parse_mpd(msg.get_payload()) # O conteúdo para extração das qualidades
        self.qi = self.parsed_mpd.get_qi() # Recuperando o vetor de qualidades do servidor
        self.saveLengthQuality(len(self.qi)) # Guardando o tamanho das qualidades em um Estado 
        self.saveDurationMovie(self.parsed_mpd.get_segment_template()) # Guarda a duração do trecho deste filme
        self.send_up(msg)

    def handle_segment_size_request(self, msg): # Pedido dos segmentos em relação a qualidade e entre outros

        msg.add_quality_id(self.qi[9])

        self.send_down(msg)

    def handle_segment_size_response(self, msg): # Tratamento da resposta dos segmentos em relação a qualidade e entre outros
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
