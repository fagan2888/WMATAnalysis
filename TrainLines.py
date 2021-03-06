'''
Created on Dec 25, 2011

@author: dmasad

A suite of functions to identify trains on a specific rail line.

'''
#from wmata import WMATA
from __future__ import division
from trainClustering import matchTrains

class Train:
    '''
    Class to hold the information and methods on trains as they are identified. 
    '''
    def __init__(self, railLine, destinationCode):
        '''
        Create a new train, associated with a RailLine object railLine.
        '''
        self.railLine = railLine
        self.lineCode = railLine.lineCode
        self.destinationCode = destinationCode
        self.listings = []     # List of all PID Listings associated with the train.
        self.arrivalTimes = {} # Dictionary of arrival times for the train, by station.
        
        
        self.nextStation = None        # Station object for the next station.
        
        self.Trains = []
        self.matched = False
        
        self.confidence = 1          # Counter of number of iterations the train has been detected.
        self.ghost = 0               # Flag for a train that has vanished from the boards, but may still be on the track.
        self.end_of_track = False    # Flag set to TRUE when the train is at the end of the track.
    
    def update_location(self, nextStation):
        '''
        The train's location is defined as the the next one it will arrive at.
        '''
        self.nextStation = nextStation
        
        
    
    def update_listings(self, newListing):
        self.listings.append(newListing)
        self.arrivalTimes[newListing['LocationCode']] = newListing['Min']
        
    def fill_listings(self):
        '''
        Estimate arrival times for stations with no associated PID listing.
        '''
        maxMinutes = 0
        for station in self.railLine.stationList[self.nextStation.seqNum:]:
            if station.stationCode in self.arrivalTimes:
                maxMinutes = self.arrivalTimes[station.stationCode]
                # Temporary hack:
                if type(maxMinutes) not in [int, float]: 
                    maxMinutes = float(maxMinutes) 
            else:
                maxMinutes += station.intervalTime()
                self.arrivalTimes[station.stationCode] = maxMinutes
        
        
    
    def findETA(self, stationCode):
        if stationCode in self.arrivalTimes:
            return self.arrivalTimes[stationCode]
        else:
            return None
    
    def advance(self, minutes):
        '''
        Advance all arrivalTimes by the given # of minutes, and adjust location accordingly.
        minutes: number of minutes to advance entries by.
        
        TODO: Project forward using estimated travel times. 
        '''
        
        for key in self.arrivalTimes:
            self.arrivalTimes[key] -= minutes
        
        while self.arrivalTimes[self.nextStation.stationCode] < 0:
            if self.nextStation.nextStation is None:
                self.end_of_track = True
                break
            else:
                self.update_location(self.nextStation.nextStation)
                 
    
    def findLocation(self):
        if self.nextStation.seqNum == 0:
            # If it is the first station, assume it's at the station.
            self.lat = self.nextStation.lat
            self.lon = self.nextStation.lon
        else:
            prevStation = self.railLine.stationList[self.nextStation.seqNum - 1]
            nextLat = self.nextStation.lat
            nextLon = self.nextStation.lon
            prevLat = prevStation.lat
            prevLon = prevStation.lon
            
            try:
                fraction = self.findETA(self.nextStation.stationCode)/self.nextStation.intervalTime()
            except:
                # In face of divide by zero error.
                fraction = 0.5
            if fraction>1: 
                # Temporary hack, until better intervalTime is resolved.
                fraction = 0.5
                #print self.railLine.lineCode, self.nextStation
            self.lat = prevLat + (nextLat - prevLat)*fraction
            self.lon = prevLon + (nextLon - prevLon)*fraction
    
class Station:
    '''
    Class to store the data relating to stations on the line.
    '''
    def __init__(self, railLine, station):
        '''
        railLine: the parent RailLine object.
        station: output from the Rail Path API Method.
        '''
        self.stationCode = station['StationCode'] # The station code
        self.stationName = station['StationName']
        self.seqNum = int(station['SeqNum']) - 1 # Adjust the sequence number to correspond to the list.
        self.arrivals = [] # List of PID entry objects associated with the station
        self.intervalTimes = [] # List of estimated times from the previous station to this one.
        
        # Pointers to the next and previous Station objects.
        self.nextStation = None
        self.prevStation = None
        
        stationData = railLine.manager.stationData[self.stationCode]
        self.lat = stationData['Lat']
        self.lon = stationData['Lon']
        
    
    def intervalTime(self):
        '''
        Compute the current estimated travel time from the previous station.
        '''
        return sum(self.intervalTimes)/len(self.intervalTimes)
    

class RailLine:
    
    def __init__(self, Manager, lineCode, reverse = False):
        '''
        Create a new object storing data on a rail line in the WMATA system.
        Manager is an initialized MEtroManager Object
        lineCode is a valid WMATA rail line code (RD, OR, BL, YL, GR)
        reverse determines the direction
        '''
        
        self.manager = Manager # An instance of MetroManager.
        self.lineCode = lineCode
        self.reverse = reverse
        
        self.stationTimes = {}
        self.Trains = []
        # List and Dictionary directories of the stations on the line.
        self.stationList = []
        self.stationDict = {}
        
        line = self.manager.lineData[self.lineCode]
        self.startStation = [line['StartStationCode'], line['InternalDestination1'] ]
        self.endStation = [line['EndStationCode'], line['InternalDestination2'] ]
        
        if self.lineCode == 'YL': # Temporary hard-coding to deal with error in WMATA Yellow Line coding:
            self.startStation = [u'C15', '']
            self.endStation[0] = u'E06'
            self.endStation[1] = u'B06'
            self.endStation.append(u'E01')
        
        if self.reverse == True: # Reverse the direction if needed: 
            self.startStation, self.endStation = self.endStation, self.startStation
        
        
        path = self.manager.getRailPath(self.startStation[0], self.endStation[0])
        
        for station in path:
            newStation = Station(self, station)
            self.stationList.append(newStation)
            self.stationDict[newStation.stationCode] = newStation
        
        for index, station in enumerate(self.stationList):
            if index < len(self.stationList)-1:
                station.nextStation = self.stationList[index + 1]
            if index > 0:
                station.prevStation = self.stationList[index - 1]
   
    
    def _matchPIDs(self, dictPID):
        '''
        Get the current PIDs from a dictionary of PIDs, keyed with a tuple of locationCode and endStation.
        '''
        
        for station in self.stationList:
            arrivals = []
            for i in range(len(self.endStation)):
                if self.endStation[i] != '':
                    arrivals = arrivals + dictPID[(station.stationCode, self.endStation[i])]
            # Clean up entries:
            for entry in arrivals:
                # Convert the arrival time to integers:
                if entry['Min'] in ['ARR', "BRD"]: 
                    entry['Min'] = 0
                else:
                    try: 
                        int_min = int(entry['Min'])
                        entry['Min'] = int_min
                    except:
                        arrivals.remove(entry) # Remove empty or nonstandard entries
            station.arrivals = sorted(arrivals, key=lambda k: k['Min'])
                
        
    
    def findTrains(self, dictPID):
        '''
        Estimate the locations of trains in the system.
        
        dictPID: A dictionary keyed with tuples (StationCode, EndStation)
            listing all relevant PID entries for that station in that direction.
        '''
        self._matchPIDs(dictPID)
        self.oldTrains = self.Trains
        self.newTrains = []

        for station in self.stationList:
            for entry in station.arrivals:
                entry['Train'] = None 
        

        startingNumber = 0
        self.trainCount = 0
        
        for station in self.stationList:
            for entry in station.arrivals:
                if entry['Train'] is None: self._seekTrainForward(startingNumber, len(self.newTrains))
            startingNumber = startingNumber + 1
        
        # Match the new trains to the old trains:
        print self.lineCode, self.reverse
        for train in self.newTrains:
            train.fill_listings()
        self.Trains = matchTrains(self.oldTrains, self.newTrains)

    def _seekTrainForward(self, startingNumber, initTrainCount, destinationCode=None):
        '''
        startingNumber: Index of station to start with.
        initTrainCount: Trains already added to the system.
        
        This function works as follows:
        Start from an initial station: 
            The first available entry (one not associated with a previous train)
            becomes a new train. 
            This arrival time becomes the current maxTime
        Move to the next station:
            If the first available entry has an arrival time > maxTime:
                Associate it with the same train; this becomes new maxTime
            If there is an available entry with time < maxTime:
                Recursively launch the function forward, so that this becomes a new train.
        Continue until all stations have been traversed.
                
        '''
        
        
        trainCount = initTrainCount
        maxWait = 0 # Maximum wait time for this train.
        # Create a new train
        for entry in self.stationList[startingNumber].arrivals:
            if entry['Train'] == None and (entry['DestinationCode']==destinationCode or destinationCode is None):
                #Associate the entry with the new train:
                trainCount = trainCount + 1
                self.trainCount = self.trainCount + 1
                newTrain = Train(self, destinationCode)
                destinationCode = entry['DestinationCode']
                # print "Creating a new train, between " + self.path[startingNumber - 1]['StationName'] + " and " +  self.path[startingNumber]['StationName']
                newTrain.update_location(self.stationList[startingNumber])
                entry['Train'] = trainCount
                newTrain.update_listings(entry)
                maxWait = entry['Min']
                entry['Train'] = trainCount
                break
        
        if trainCount == initTrainCount: return initTrainCount
        
        # Now advance forward:
        # TODO: replace counter with enumerate.
        counter = startingNumber + 1
        while counter < len(self.stationList):
            for entry in self.stationList[counter].arrivals:
                if entry['Train'] == None: 
                    if entry['Min'] > maxWait and entry['DestinationCode']==destinationCode:
                        entry['Train'] = trainCount
                        newTrain.update_listings(entry)
                        maxWait = entry['Min']
                        break
                    elif entry['DestinationCode']==destinationCode:
                        self._seekTrainForward(counter, self.trainCount, destinationCode)
                    else:
                        self._seekTrainForward(counter, self.trainCount)
            counter = counter + 1
        self.newTrains.append(newTrain)
        
                    
    def updateStationIntervals(self):
        '''
        Run only after locating trains.
        Update the estimates of the travel time from station to station based on current PID data.
        
        TODO: Make more elegant.
        This is an hacked-together temporary solution.
        Eventually, implement a full database and pull timings based on day/time.
        '''
        for index, station in enumerate(self.stationList[1:]): # Index starts counting from 0.
            station.intervalTimes = []
            for train in self.Trains:
                etaStation = train.findETA(station.stationCode)
                etaPrev = train.findETA(self.stationList[index].stationCode) # Index here = actual index - 1
                if etaStation != None and etaPrev != None:
                    timing = etaStation - etaPrev
                    station.intervalTimes.append(timing)