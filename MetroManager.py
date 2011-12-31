'''
Created on Dec 29, 2011

@author: dmasad
'''
import json
from TrainFinder import RailLine
from wmata import WMATA

LINES = ["RD", "OR", "BL", "YL", "GR"]

class WMATAManager:
    '''
    A class intended to manage pulling data for the entire Metro system
    '''

    def __init__(self, api_key):
        '''
        Initialize the system with a valid WMATA API key
        '''
        self.api = WMATA(api_key)
        
        self.rail_lines = []
        for line in LINES:
            for direction in [True, False]:
                self.rail_lines.append(RailLine(self.api, line, reverse=direction))
    
    def updateLines(self):
        self.api.updateSchedule()
        # Save the current schedule in order to minimize API calls.
        self.api.saveSchedule("CurrentSchedule.json")
        for line in self.rail_lines:
            line.findTrains("CurrentSchedule.json")
            line.updateStationTiming()
    
    def exportSchedules(self, filepath):
        '''
        Write the current timing between stations to a JSON file.
        '''
        all_timings = []
        for line in self.rail_lines:
            timing = {}
            timing['Line'] = line.lineCode
            timing['reverse'] = line.reverse
            timing['timing'] = line.stationTimes
            all_timings.append(timing)
        
        f = open(filepath, "w")
        json.dump(all_timings, f)
        f.close()
    
    def importSchedule(self, filepath):
        f = open(filepath, "r")
        all_timings = json.loads(f.read())
        f.close()
        
        for line in self.rail_lines:
            for timing in all_timings:
                if timing['Line'] == line.lineCode and timing['reverse'] == line.reverse:
                    line.stationTimes = timing['timing'] 
        
        
        
        