'''
Created on Dec 25, 2011

@author: dmasad

A suite of functions to identify trains on a specific rail line.

'''
from wmata import WMATA

class Train:
    def __init__(self, lineCode, destinationCode):
        self.lineCode = lineCode
        self.destinationCode = destinationCode
        self.listings = []
    
    def update_location(self, nextStation):
        '''
        The train's location is defined as the the next one it will arrive at.
        '''
        self.nextStation = nextStation
    
    def update_listings(self, newListing):
        self.listings.append(newListing)

class RailLine:
    
    def __init__(self, API, lineCode, reverse = False):
        '''
        Create a new object storing data on a rail line in the WMATA system.
        API is an initialized WMATA API
        lineCode is a valid WMATA rail line code (RD, OR, BL, YL, GR)
        reverse determines the direction
        '''
        
        self.api = API # An instance of the WMATA API
        self.lineCode = lineCode
        self.reverse = reverse
        
        allLines = self.api.getRailLines(True) # Get data on all lines as a dict
         
        self.startStation = [allLines[self.lineCode]['StartStationCode'], allLines[self.lineCode]['InternalDestination1'] ]
        self.endStation = [allLines[self.lineCode]['EndStationCode'], allLines[self.lineCode]['InternalDestination2'] ]
        if self.reverse == True: # Reverse the direction if needed: 
            self.startStation, self.endStation = self.endStation, self.startStation
        
        
        self.path = self.api.getRailPath(self.startStation[0], self.endStation[0])
        
        for station in self.path:
            station['Arrivals'] = []
    
    def _matchPIDs(self, filepath=None):
        '''
        Get the current PIDs and add them to the relevant stations.
        After running this function, each station in the path list will have an 'Arrivals' key
        which will hold a list of PID entries.
        
        filepath: Filepath of a saved JSON schedule to load.
        '''
        currentPIDs = self.api.getSchedule(saved_filepath=filepath)
        # Loop across all stations and find the appropriate PID entries
        for station in self.path:
            arrivals = []
            for entry in currentPIDs:
                if entry['DestinationCode'] == '': continue #Skip blank destination codes.
                if entry['LocationCode'] == station['StationCode'] and entry['DestinationCode'] in self.endStation:
                    # Convert the arrival time to integers:
                    if entry['Min'] in ['ARR', "BRD"]: 
                        entry['Min'] = 0
                    else:
                        try: 
                            entry['Min'] = int(entry['Min'])
                        except:
                            continue # Ignore empty or nonstandard entries
                         
                    arrivals.append(entry)
            station['Arrivals'] = arrivals
    """
    DEPRECATED FUNCTIONS:
    def findTrains(self):
        '''
        Estimate the locations of trains in the system.
        '''
        self.Trains = []
        
        startingNumber = 0
        while self.path[startingNumber]['Arrivals'] == []:
            startingNumber = startingNumber + 1
        for i in range(len(self.path[startingNumber]['Arrivals'])):
            self.seekTrainForward(startingNumber, i)
        
    
    def seekTrainForward(self, startingNumber, startingRank):
        '''
        startingNumber: Index of station to start with
        startingRank: Rank of arriving train to count from. 0==First, 1==Second etc. 
        
        Treats the train at Rank startingRank arriving at station startingNumber as a new train.
        Assumes that a train at the next station with arrivalTime > arrivalTime at the current station is the same train.
        If it finds a train with lower arrivalTime, treat that as a new train and begin the process again.
        
        Returns the index of the final train station it found values for.
        
        '''
        rank = startingRank
        maxStation = startingNumber
        # Create a new train:
        if len(self.path[startingNumber]['Arrivals'])<rank+1: return startingNumber
        newTrain = Train(self.lineCode, self.endStation)
        print "Creating a new train, between " + self.path[startingNumber - 1]['StationName'] + " and " +  self.path[startingNumber]['StationName']
        newTrain.update_location(self.path[startingNumber]['StationCode'])
        newTrain.update_listings(self.path[startingNumber]['Arrivals'][rank])
        
        #Now advance forward:
        counter = startingNumber + 1
        while counter < len(self.path):
            if len(self.path[counter]['Arrivals'])<rank+1: break
            
            if self.path[counter]['Arrivals'][rank]['Min'] > self.path[counter-1]['Arrivals'][rank]['Min']:
                newTrain.update_listings(self.path[counter]['Arrivals'][rank])     
            else:
                maxStation = max(counter, self.seekTrainForward(counter, rank))
                if len(self.path[counter]['Arrivals'])>rank+1:
                    rank = rank + 1
                    if self.path[counter]['Arrivals'][rank]['Min'] > self.path[counter-1]['Arrivals'][rank-1]['Min']:
                        newTrain.update_listings(self.path[counter]['Arrivals'][rank])
                else: break
            counter = counter + 1     
        self.Trains.append(newTrain)
        return max(maxStation, counter)
    """
    
    def findTrains(self, filepath = None):
        '''
        Estimate the locations of trains in the system.
        filepath: Path for a saved JSON schedule to load, for testing purposes.
        '''
        self._matchPIDs(filepath)
        self.Trains = []

        for station in self.path:
            for entry in station['Arrivals']:
                entry['Train'] = None 
        
        startingNumber = 0
        while self.path[startingNumber]['Arrivals'] == []:
            startingNumber = startingNumber + 1

        self.trainCount = 0
        for entry in self.path[startingNumber]['Arrivals']:
            self._seekTrainForward(startingNumber, len(self.Trains))
    
    
    def _seekTrainForward(self, startingNumber, initTrainCount):
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
        for entry in self.path[startingNumber]['Arrivals']:
            if entry['Train'] == None:
                #Associate the entry with the new train:
                trainCount = trainCount + 1
                self.trainCount = self.trainCount + 1
                newTrain = Train(self.lineCode, self.endStation)
                print "Creating a new train, between " + self.path[startingNumber - 1]['StationName'] + " and " +  self.path[startingNumber]['StationName']
                newTrain.update_location(self.path[startingNumber]['StationCode'])
                entry['Train'] = trainCount
                newTrain.update_listings(entry)
                maxWait = entry['Min']
                entry['Train'] = trainCount
                break
        
        if trainCount == initTrainCount: return initTrainCount
        
        # Now advance forward:
        counter = startingNumber + 1
        while counter < len(self.path):
            for entry in self.path[counter]['Arrivals']:
                if entry['Train'] == None: 
                    if entry['Min'] > maxWait:
                        entry['Train'] = trainCount
                        newTrain.update_listings(entry)
                        maxWait = entry['Min']
                        break
                    else:
                        self._seekTrainForward(counter, self.trainCount)
            counter = counter + 1
        self.Trains.append(newTrain)
        
                    
        