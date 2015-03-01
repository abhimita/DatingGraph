#!/usr/bin/env python
import gviz_api
import cgi, cgitb, os, sys

if __name__ == '__main__':

    reqId = 0
    query_string = os.environ.get('QUERY_STRING')

    form = cgi.FieldStorage()
    if form.has_key("tqx"):
        tqx = form.getvalue("tqx")
        if tqx.find("reqId") != -1:
            reqId = int(tqx[tqx.find("reqId"):].split(":")[1])

    print "Content-type: text/plain"
    print

    if form.has_key("qt"):
       if form.getvalue("qt") in ["node_cnt","edge_cnt"]:
           with open("/home/abhattac/graph/dating_graph_size.txt","r") as fp:
               txt = fp.read().strip()
           data = {} 
           for line in txt.split('\n'):
               fields = line.split(',')
               if not data.has_key(fields[0] + '~' + fields[1]):
                   data[fields[0] + '~' + fields[1]] = []
               data[fields[0] + '~' + fields[1]].append((fields[0],int(fields[2]),int(fields[3])))
           celebrityList = list(set([k.split('~')[0] for k in data.keys()]))
          
           pivotedList = [] 
           lastValue = {}
           schema = { "level" : ("number" , "Level")}
           columnsOrder = ['level']
           for c in celebrityList:
               schema[c.lower().replace(' ','_') + '_cnt'] = ("number", c)
               columnsOrder.append(c.lower().replace(' ','_') + '_cnt')

           for level in range(1,11):
               pivotedList.append({'level' : level})
               for c in celebrityList:
                   key = c + '~' + str(level)
                   if data.has_key(key):
                       lastValue[c] = (data[key][0][1] if form.getvalue("qt") == "node_cnt" else data[key][0][2])
                   pivotedList[level -1][c.lower().replace(' ','_') + '_cnt'] = lastValue[c] 
 
           dataTable = gviz_api.DataTable(schema)
           dataTable.LoadData(list(pivotedList))
  
           print dataTable.ToJSonResponse(columns_order=columnsOrder,req_id=reqId)
     

