from r2a.ir2a import IR2A
from player.parser import *
import datetime
import json
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


def avg(myList):
    return sum(myList)/len(myList)

def avgLastMostSignificant(myList):
    weight = 0
    average = 0
    for i in range(len(myList)):
        weight += (i + 1)/2
        average += (i+1)*myList[i]/2
    average = average/weight
    return average

class R2Bandwith(IR2A):

    # ---------------- ATRIBUTOS ------------------------

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.lengthQuality = 0 # Inicializando o estado de qualidades
        self.durationMovie = 0
        self.lengthInBit = []
        self.timeOfRequest = []
        self.bufferThroughput = []
        self.ConfigParameters = {}

    # ------------------ Métodos -----------------------

    def saveLengthQuality(self, lengthToAdd):
        self.lengthQuality = lengthToAdd

    def saveDurationMovie(self, durationMovie):
        self.durationMovie = int(durationMovie['duration'])

    def saveLengthInBitSection(self, LengthInBit):
        self.lengthInBit += [LengthInBit]

    def bufferOfTime(self, timeToSave):
        self.timeOfRequest += [timeToSave]

    def addBufferThroughput(self, throughputToBuffer):
        self.bufferThroughput += [throughputToBuffer]


    # ------------------ API's ------------------------

    def handle_xml_request(self, msg): # Envio do pedido da requisição
        self.send_down(msg)

    def handle_xml_response(self, msg): # Tratamento da reposta Inicial

        self.parsed_mpd = parse_mpd(msg.get_payload()) # O conteúdo para extração das qualidades
        self.qi = self.parsed_mpd.get_qi() # Recuperando o vetor de qualidades do servidor
        self.saveLengthQuality(len(self.qi)) # Guardando o tamanho das qualidades em um Estado
        self.saveDurationMovie(self.parsed_mpd.get_segment_template()) # Guarda a duração do trecho deste filme
        self.send_up(msg)

    def handle_segment_size_request(self, msg): # Pedido dos segmentos em relação a qualidade e entre outros
        time_stop = datetime.datetime.now() # Pegando o tempo atual para o calculo da vazão
        self.bufferOfTime(time_stop.timestamp())

        bufferWhiteBoard = self.whiteboard.get_playback_buffer_size() # buffer do tempo da requisição correlacionado com ao arquivo
        throughput = 0
        maxThroughput = 2
        movingAvarageFactor = 5 # Variável para fazer a média das últimas qualidades usadas para não haver uma mudança brusca
        qualityMovingAverage = 0
        averageQuality = 8 # qualidade inicial para qualidade
        averageConnectionThroughput = -1
        debugger = True

        if len(self.timeOfRequest) > 2:
            timeRequest = self.timeOfRequest[-1] - self.timeOfRequest[-2]
            throughput = self.lengthInBit[-1] / timeRequest
            self.addBufferThroughput(throughput)
            maxThroughput = max(self.bufferThroughput)
            averageConnectionThroughput = avg(self.bufferThroughput[-20:]) # Pega o vetor o vetor do -20 em diante

        if len(bufferWhiteBoard) > 0:
            bufferWhiteBoard = bufferWhiteBoard[-1][1]
        else:
            bufferWhiteBoard = 0

        bufferQuality = self.whiteboard.get_playback_qi() # Vetor Duplo que pega o tempo do dado coletado com a qualidade observada

        if len(bufferQuality) > 0:
            averageQuality = bufferQuality
            bufferQuality = bufferQuality[-movingAvarageFactor:] # Pegando o buffer das qualidades da ultimas a partir da taxa selecionada anteriormente
            bufferQuality = [item[1] for item in bufferQuality]
            qualityMovingAverage = avg(bufferQuality)
            averageQuality = averageQuality[-20:] # O Valor mádio das qualidades
            averageQuality = [item[1] for item in averageQuality]
            averageQuality = avgLastMostSignificant(averageQuality)
        else:
            qualityMovingAverage = 0

        if debugger:
                print(f'Debugger Qualidade Média: {averageQuality}')

        sizeBufferMax = self.ConfigParameters["max_buffer_size"]
        if len(self.timeOfRequest) < 4:
            averageBufferSize = 0.5 * sizeBufferMax
        else:
            averageBufferSize = 0.6 * sizeBufferMax - (0.4 * sizeBufferMax*(self.timeOfRequest[-1] - self.timeOfRequest[0]) / self.durationMovie) # Média do tamanho do tempo das requisição
            if averageBufferSize < 0.2 * sizeBufferMax: # Se for 1/5 do maxímo necessário
                averageBufferSize = 0.2 * sizeBufferMax
        if debugger:
                print(f'Debugger Média dos tempos de requisição: {averageBufferSize}')

        maxThroughputStep = 1
        if maxThroughput > 100:
            maxThroughputStep = maxThroughput / 40
        connectionThroughput = ctrl.Antecedent(np.arange(0, maxThroughput, maxThroughputStep), 'connection_throughput')
        buffer = ctrl.Antecedent(np.arange(0, sizeBufferMax + 1, 1), 'buffer')
        quality = ctrl.Consequent(np.arange(0, self.lengthQuality, 1), 'quality')

        if averageConnectionThroughput == -1:
            averageConnectionThroughput = maxThroughput/2

        # Faixa da taxa de transmissão com 3 categorias
        connectionThroughput['poor'] = fuzz.trimf(connectionThroughput.universe, [0, 0, round(maxThroughput)])
        connectionThroughput['average'] = fuzz.trimf(connectionThroughput.universe, [0, round(averageConnectionThroughput), round(maxThroughput)])
        connectionThroughput['good'] = fuzz.trimf(connectionThroughput.universe, [round(averageConnectionThroughput), round(maxThroughput), round(maxThroughput)])

        # Faixa dos Tamanhos do Buffer
        buffer['low'] = fuzz.trimf(buffer.universe, [0, 0, round(averageBufferSize)])
        buffer['normal'] = fuzz.trimf(buffer.universe, [0, round(averageBufferSize), sizeBufferMax])
        buffer['high'] = fuzz.trimf(buffer.universe, [round(averageBufferSize), sizeBufferMax, sizeBufferMax])

        # Faixa das Qualidades
        quality['low'] = fuzz.trimf(quality.universe, [0, 0, round(averageQuality)])
        quality['normal'] = fuzz.trimf(quality.universe, [0, round(averageQuality), self.lengthQuality - 1]) # self.lengthQuality preciso que o tamanho seja menor que 1
        quality['high'] = fuzz.trimf(quality.universe, [round(averageQuality), self.lengthQuality - 1, self.lengthQuality - 1])

        #Regras para as requisições
        rule1 = ctrl.Rule(connectionThroughput['poor'] | buffer['low'], quality['low'])
        rule2 = ctrl.Rule(connectionThroughput['average'] , quality['normal'])
        rule3 = ctrl.Rule(connectionThroughput['good'] & buffer['low'], quality['normal'])
        rule4 = ctrl.Rule(connectionThroughput['good'] & buffer['high'], quality['high'])

        ctrlQuality = ctrl.ControlSystem([rule1, rule2, rule3, rule4])
        newQuality = ctrl.ControlSystemSimulation(ctrlQuality)

        newQuality.input['buffer'] = bufferWhiteBoard
        newQuality.input['connection_throughput'] = throughput
        newQuality.compute()

        qualityMovingAverage = avg([qualityMovingAverage, newQuality.output['quality']])
        if debugger:
                print(f'Debugger Nova Qualidade do vídeo: {qualityMovingAverage}')

        qualityMovingAverage = int(round(qualityMovingAverage))

        msg.add_quality_id(self.qi[qualityMovingAverage])
        self.send_down(msg)

    def handle_segment_size_response(self, msg): # Tratamento da resposta dos segmentos em relação a qualidade e entre outros
        bitLengthSection = msg.get_bit_length() # Pegando o tamanho da seção em Bit para criar um buffer para taxa de transmissão
        self.saveLengthInBitSection(bitLengthSection)
        self.send_up(msg)

    def initialize(self):
        with open('dash_client.json') as f:
            self.ConfigParameters = json.load(f)
        pass

    def finalization(self):
        pass
