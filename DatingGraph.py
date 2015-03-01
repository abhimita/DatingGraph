#!/usr/bin/env python
import os
import sys
import urllib
import requests
import re
import pprint
import pydot
import shutil
import textwrap
import networkx as nx 
from networkx.readwrite import json_graph

pp = pprint.PrettyPrinter(indent=4) 

siteUrl = 'http://www.zimbio.com/'
fileDir = '/home/abhattac/graph/'

class DatingGraph:

    def __init__(self,celebrity):
        # Initialization
        self.celebrity = celebrity
        self.relationship = []
        self.nxg = nx.DiGraph(Name='Relationship') # NetworkX graph
        self.relationTypes = { \
            'was engaged to' : {'type' : 'engagement', 'time' : 'past'},\
            'is engaged to' : {'type' : 'engagement', 'time' : 'present'},\
            'dated' : {'type' : 'dating', 'time' : 'past'},\
            'is dating': {'type' : 'dating', 'time' : 'present'},\
            'had a fling with': {'type' : 'fling', 'time' : 'past'},\
            'was rumored to be with': {'type' : 'rumor', 'time' : 'past'},\
            'is rumored to be with': {'type' : 'rumor', 'time' : 'present'},\
            'was married to': {'type' : 'marriage', 'time' : 'past'},\
            'is married to': {'type' : 'marriage', 'time' : 'present'}
        }
                                                                                                                            

    def getText(self, celebrity):
        # Gets the short description about celebrity from the text file 
        # dump while scraping the web page
        try:
            with open(celebrity.replace(' ','_') + '.txt','r') as fp:
                bio = fp.read()
                # Remove the last line which is often "Check the link for additional details"
                bio = re.sub(r'(Find|Check|See) .*','',bio)
                return bio
        except IOError:
                return None

    def getImage(self, celebrity):
        url = siteUrl + celebrity.replace(' ','+')
        r = requests.get(url)
        if r.status_code == 200:
            # Scrape the web page to get the image file
            imageUrl = re.findall(r'<img class="mugshotImage" src="(.*?)" .*',r.text)
            if os.path.exists(celebrity.replace(' ','_') + '.jpg'): return 
            try:
                # Additional call to download the image file
                try:
                    image = requests.get(imageUrl[0], stream=True)
                    with open(celebrity.replace(' ','_') + '.jpg','wb') as out_file:
                        shutil.copyfileobj(image.raw, out_file)
                    del image
                except requests.exceptions.ConnectionError:
                    pass
            except IndexError:
                pass

            # Regular expression pattern to extract long/short description (overview) of the celebrity
            regexpList = [r'<div id="ovLong">(.*?)</div>', \
                          r'<div id="ovShort">(.*?)</div>', \
                          r'<div id="voLong">(.*?)</div>', \
                          r'<div id="voShort">(.*?)</div>']   

            for exp in regexpList:
                bio = re.findall(exp, r.text)
                if len(bio) != 0:
                    # Extract text providing overview
                    with open(celebrity.replace(' ','_') + '.txt','w') as out_file:
                        out_file.write(bio[0].encode('utf-8'))
                    # Discontinue the loop if one overview is found
                    break


    def extractRelationship(self,level=1):

        stack = []
        stack.append((self.celebrity,0)) # Stack used for recursion 
        alreadySeen = {} # dictionary to keep track of celebrity name already 
        
        # Marriage / dating is a two way relationship. A is married to B
        # also means that B is married to A. Because I didn't plan to draw
        # an edge with arrows at both ends so only one side of the relationship
        # is depicted in SVG diagram. This dictionary is used to capture one 
        # side of the relationship and eliminate the other one to reduce 
        # clutter
        pair = {}

        while len(stack) > 0:
            
            c = stack.pop()
            if c[1] >= level: continue
            alreadySeen[c[0]] = True
            self.getImage(c[0]) # Dump the image file for the celebrity
            url = siteUrl + c[0].replace(' ','+') + '/dating' # URL for dating history
            print "Accessing URL: %s (Level: %d)" % (url, c[1] + 1)
            r = requests.get(url) 
            if r.status_code == 200:
                relationships = re.findall('<div class="topicHeadline hd2 lnk1">\n<a href=".*?">(.*?)</a>\n</div>',r.text.encode('utf-8'),re.M)

            # Process all relationships
            for rel in relationships:
                for k in self.relationTypes:
                    # Example A dated B -> [1] firstCelebrity = A [2] secondCelebrity = B
                    #                      [3] verb = dated
                    s = re.match(r'(.*?)\s+%s\s+(.*)' % k,rel)
                    if s is not None:
                        firstCelebrity = s.group(1) 
                        verb = k
                        secondCelebrity = s.group(2) 
                        break

                # A dated B means while traversing relationship graph for B we expect to see 
                # B dated A
                # Check if the pair (A,B) or (B,A) has already been added
                # If yes then skip that step
                if not pair.has_key(secondCelebrity + '~' + firstCelebrity) and \
                   not pair.has_key(firstCelebrity + '~' + secondCelebrity):
                    self.relationship.append(
                        { 'firstCelebrity' : firstCelebrity,
                          'secondCelebrity' : secondCelebrity,
                          'relationType' : self.relationTypes[verb]['type'], # e.g. dated, married,....
                          'timeFrame' : self.relationTypes[verb]['time'] , # e.g. past / present relationship
                          'verb' : verb,
                          'level' : c[1]
                        }
                    )
                    pair[firstCelebrity + '~' + secondCelebrity] = True
                    pair[secondCelebrity + '~' + firstCelebrity] = True

                # Traverse the relationship graph is the second celebrity has not been processed already
                if not alreadySeen.has_key(secondCelebrity) :
                    stack.append((secondCelebrity, c[1] + 1))
                    self.getImage(secondCelebrity) 
        print "Completed extracting relationship data" 

 

    def findPath(self, jsonFile, celebrity):
        nxg = json_graph.load(open(jsonFile))
        for n in nxg.nodes(data=True):
            if nxg.in_degree(n[0]) == 0:
                rootNode = n
                break 
        reverseNxg = nxg.reverse(copy=True)
        for node in reverseNxg.nodes(data=True):
            if node[1]['name'] == celebrity:
                for p in nx.all_simple_paths(reverseNxg,node[0],rootNode[0]):
                    print [nxg.node[x]['name'] for x in p]
                break 
                        
    def analyzeGraph(self, jsonFile, level=10):
        data = []
        nxg = json_graph.load(open(jsonFile))
        for n in nxg.nodes(data=True):
            if nxg.in_degree(n[0]) == 0:
                rootNode = n
                break 
        paths = nx.single_source_shortest_path(nxg,rootNode[0],level)
        nodes = {} # Dictionary to keep track of nodes at length x from root node
        for k,v in paths.items():
            if k == rootNode[0]: continue # exclude root node
            if not nodes.has_key(len(v) - 1):
                nodes[len(v) - 1] = []
            nodes[len(v) - 1].append(k)
                                     
#        cTotal = 0 # cumulative total

        for k in sorted(nodes.keys()):
            bunch = [rootNode[0]]
            for i in range(1,k + 1):
                bunch.extend(nodes[i])
            subgraph = nxg.subgraph(bunch)
            data.append({'name' : rootNode[1]['name'],
                         'level' : k,
                         'node_cnt' : subgraph.number_of_nodes(),
                         'edge_cnt' : subgraph.number_of_edges()})
        return data
 
    def generateNXModel(self, outFile):
        nodeLookup = {}
        index = 1
        for r in self.relationship:
            if not nodeLookup.has_key(r['firstCelebrity']):
                self.nxg.add_node(index, {'name' : r['firstCelebrity']})
                nodeLookup[r['firstCelebrity']] = index
                index = index +  1
            if not nodeLookup.has_key(r['secondCelebrity']):
                self.nxg.add_node(index, {'name' : r['secondCelebrity']})
                nodeLookup[r['secondCelebrity']] = index
                index = index +  1
        for r in self.relationship:
           self.nxg.add_edge(nodeLookup[r['firstCelebrity']], 
                             nodeLookup[r['secondCelebrity']], 
                             {'verb' : r['verb'], 
                              'timeFrame' : r['timeFrame'], 
                              'relationType' : r['relationType'],
                              'level' : r['level']})

        # Dump Json for NetworkX graph
        with open(outFile + '.json','w') as fp:
            fp.write(json_graph.dumps(self.nxg,indent=4) + '\n')        
            
    def drawGraph(self,outFile):
        graph = pydot.Dot(graph_type='digraph', graph_name='Relationship', 
                          rankdir='TB', overlap=False, simplify=True,
                          nodesep=0.10, ranksep=0.10, minlen=0, 
                          center=True, ratio='auto') 
                               
        for n in self.nxg.nodes(data=True):
            if self.nxg.in_degree(n[0]) == 0:
                rootNode = n
                break 
        paths = nx.single_source_shortest_path(self.nxg,rootNode[0],4) # go to max 4 levels
        nodes = {}
        for k,v in paths.items():
            nodes[k] = True
        subg = self.nxg.subgraph(nodes.keys())
        processedNode = {}
        
        for node in subg.nodes(data=True):                                            
            if processedNode.has_key(node[1]['name']):
                # Node already exists. Get its reference
                sourceNode = processedNode[node[1]['name']]
            else:
                bio = self.getText(node[1]['name'])
                if bio is not None: 
                    tooltipText = node[1]['name'] + ':' + '&#10;' + bio # Add overview along-with full name
                else:
                    tooltipText = node[1]['name'] # No overview found for the celebrity
                sourceNode = pydot.Node(node[0], shape='rect',
                                        image=fileDir + node[1]['name'].replace(' ','_') + '.jpg' ,
                                        fixedsize=True, fontsize=6, width=0.3,
                                        fontcolor="red",
                                        height=0.30,style='filled,rounded',
                                        labelloc="t", # Lalel location is top
                                        label=node[1]['name'].split()[0],
                                        tooltip=tooltipText)
                processedNode[node[1]['name']] = sourceNode
                graph.add_node(sourceNode)

                
        for edge in subg.edges(data=True): 
            # Arrow style based on relationship
            if edge[2]['relationType'] == 'engagement':
                arrowStyle = "diamond"
            elif edge[2]['relationType'] == 'marriage':
                arrowStyle = "normal"
            elif edge[2]['relationType'] == 'dating':
                arrowStyle = "ediamond"
            elif edge[2]['relationType'] == 'fling':
                arrowStyle = "vee"
            elif edge[2]['relationType'] == 'rumor':
                arrowStyle = "crow"
 
            graph.add_edge(pydot.Edge(processedNode[self.nxg.node[edge[0]]['name']], 
                                      processedNode[self.nxg.node[edge[1]]['name']],
                                      label=edge[2]['relationType'] + ' ' + edge[2]['timeFrame'],
                                      edgetooltip=self.nxg.node[edge[0]]['name'] + ' ' + edge[2]['verb'] + ' ' + self.nxg.node[edge[1]]['name'], 
                                      style='dashed' if edge[2]['timeFrame'] == 'past' else 'solid',
                                      color='green' if edge[2]['timeFrame'] == 'present' else 'red',
                                      arrowhead=arrowStyle,
                                      fontsize=6))            
        
        graph.write_svg(outFile + '.svg')
        # svg is generated assuming file will be used locally.
        # Substitue local path with URL in case svg is served from web server
        svgContent = open(outFile + '.svg','r').read().replace(fileDir,"")
        with open(outFile + '.svg','w') as fp:
            fp.write(svgContent + '\n')
            
        

if __name__ == '__main__':

    celebrityList = ['Britney Spears','Shakira','Jennifer Lopez','Keanu Reeves',\
                     'Kim Kardashian' ,'Katy Perry','Taylor Swift','Michael Douglas','Brad Pitt',\
                     'Justin Bieber','Adam Levine','Ashton Kutcher','Michael Keaton'] 


#    for c in celebrityList:
#        print "Processing: %s..." % c
#        datingGraph = DatingGraph(c)
#        datingGraph.extractRelationship(level=10) 
#        datingGraph.generateNXModel(c.lower().replace(' ','_'))
#        datingGraph.drawGraph(c.lower().replace(' ','_'))        

#    data = []
#    for c in celebrityList:
#        datingGraph = DatingGraph(c)
#        data.extend(datingGraph.analyzeGraph(c.lower().replace(' ','_') + '.json'))
#    fp = open('dating_graph_size.txt','w') 

#    for d in data:
#        fp.write(d['name'] + ',' + str(d['level']) + ',' + str(d['node_cnt']) + ',' + str(d['edge_cnt']) + '\n')
#    fp.close()
    
    datingGraph = DatingGraph('Jennifer Lopez')
    datingGraph.findPath('jennifer_lopez.json','Nicolas Sarkozy') 
        

